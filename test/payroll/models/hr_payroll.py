# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb
import logging
from . import hr_payroll_mixin

_logger = logging.getLogger(__name__)


class HrPayroll(models.Model):
    _name = "hr.payroll"
    _description = "Nómina"

    name = fields.Char(string="Nombre", required=True, default="Nómina")
    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin", required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Cerrada'),
    ], string="Estado", default="draft")

    line_ids = fields.One2many("hr.payroll.line", "payroll_id", string="Líneas de nómina")

    # -------------------------
    # Helpers pequeños
    # -------------------------
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return { 
                # Employee info
                'employee_id':0.0,
                'contract_id': 0.0,
                'base_wage': 0.0,
                'wage_earned': 0.0,
                'days_worked': 0.0,
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'transportation_allowance': 0.0,
                'night_surcharge': 0.0,
                'other_earnings':0.0,
                'gross': 0.0,
                'health_contribution': 0.0,
                'pension_contribution': 0.0, 
                'other_deductions': 0.0,
                'deductions': 0.0,
                'net':0.0,
                
                # Employer contributions
                'arl_contribution': 0.0,
                'total_deductions': 0.0,
                'company_health_contribution': 0.0, 
                'company_pension_contribution': 0.0,
                'total_net': 0.0,
                
                # Social benefits
                'service_bonus': 0.0,
                'severance': 0.0,
                'interest_on_severance': 0.0,
                'vacations': 0.0,
                'total_provisions': 0.0,
        }
        
    # -------------------------
    # Acción principal
    # -------------------------
    def action_generate_lines(self):
        """Genera automáticamente una línea de nómina consolidada por empleado."""
        self.ensure_one()
   
        # Valida fechas
        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")
        
        # --------------------------
        # Trae parámetros necesarios
        # --------------------------     
        # Trae empleados con contrato activo
        employees = self.env['hr.payroll.mixin']._get_employees_with_contracts(self.date_start, self.date_end)
        lines = []
        # Variables base por empleado y contrato
        for employee, contract in employees.items():
            # Trae eventos del empleado en el rango de fechas
            events = self.env['hr.payroll.mixin']._get_events(employee.id, self.date_start, self.date_end)
            
            # Trae los parámetros necesarios
            parameters = self.env['hr.payroll.mixin']._get_parameter(self.date_start)
            # Poner en variables locales para facilitar lectura
            transportation_allowance = parameters['transport_allowance']
            company_pension_percentage = parameters['company_pension_percentage']
            company_health_percentage = parameters['company_eps_percentage']
            employee_eps_percentage = parameters['employee_eps_percentage']
            employee_pension_percentage = parameters['employee_pension_percentage']
            minimun_wage = parameters['minimum_wage']
            arl_fee = parameters['arl_fee']
            # Días esperados en el período
            expected = self.env['hr.payroll.mixin']._expected_workdays(self.date_start, self.date_end)

            

            # Acumulador de totales        
            totals = self._empty_totals()
            # Dias sin pagar
            unpaid_days = self.env['hr.payroll.mixin']._compute_days_worked(events, totals, self.date_start, self.date_end)

            

            days_worked = max(0, expected - unpaid_days)
            

            if unpaid_days > expected:
                unpaid_days = expected
                days_worked = 0
            wage_earned = (contract.wage * (days_worked / expected)) if expected else 0.0
            
            allow_value = self.env['hr.payroll.mixin']._compute_transport_allowance(
                wage_earned, days_worked, minimun_wage, transportation_allowance
            )
            
            # Total devengado
            total_gross = wage_earned + totals.get('sick', 0.0) + totals.get('arl', 0.0) \
                          + totals.get('extra_hours', 0.0) + totals.get('night_surcharge', 0.0) \
                          + totals.get('comissions', 0.0) + totals.get('other', 0.0) + allow_value
                          
            benefits = self.env['hr.payroll.mixin']._compute_benefits(total_gross, wage_earned, days_worked)

            contributions = self.env['hr.payroll.mixin']._compute_contributions(
                arl_fee,
                company_health_percentage,
                employee_eps_percentage,
                company_pension_percentage,
                employee_pension_percentage,
                minimun_wage,
                total_gross,
                allow_value
            )
            
            health_contributions = contributions['employee_eps']
            pension_contributions = contributions['employee_pension']
            company_health_contribution = contributions['company_eps']
            company_pension_contribution = contributions['company_pension']
            arl_fee_value = contributions['arl_contribution']
            
            total_deductions_employee = health_contributions + pension_contributions
            total_deductions = total_deductions_employee + arl_fee_value
            
            totals['service_bonus'] = benefits['service_bonus']
            totals['severance'] = benefits['severance']
            totals['interest_on_severance'] = benefits['interest_on_severance']
            totals['vacations'] = benefits['vacations']
            totals['total_provisions'] = (
                benefits['service_bonus'] +
                benefits['severance'] +
                benefits['interest_on_severance'] +
                benefits['vacations']
            )
            

    
            # ==========================
            # Construcción de la línea de nómina
            # ==========================
            vals_line = {
                'employee_id': employee.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,
                'wage_earned': wage_earned,
                'days_worked': days_worked,
                'sick_leave': totals.get('sick', 0.0)+ totals.get('arl', 0.0),
                'overtime_hours': totals.get('extra_hours', 0.0),
                'transportation_allowance': allow_value,
                'night_surcharge': totals.get('night_surcharge', 0.0),
                'other_earnings': totals.get('comissions', 0.0) + totals.get('other', 0.0),
                'gross': total_gross,
                'health_contribution': health_contributions,
                'pension_contribution': pension_contributions,
                'company_health_contribution': company_health_contribution,
                'company_pension_contribution': company_pension_contribution,
                'arl_contribution': arl_fee_value,
                'other_deductions': 0.0,
                'deductions': total_deductions_employee,
                'total_deductions': total_deductions,
                'net': total_gross - total_deductions,
                'total_net': total_gross - total_deductions,
                
                'service_bonus': totals['service_bonus'],
                'severance': totals['severance'],
                'interest_on_severance': totals['interest_on_severance'],
                'vacations': totals['vacations'],
                'total_provisions': totals['total_provisions'],
            }
            lines.append((0, 0, vals_line))

            # ==========================
            # Logging de resultados por empleado
            # ==========================
            _logger.info("Payroll: emp=%s expected=%s unpaid_days=%s days_worked=%s totals=%s",
                         employee.name, expected, unpaid_days, days_worked, totals)

        # ==========================
        # Escritura de líneas (limpiando las anteriores)
        # ==========================
        self.line_ids = [(5, 0, 0)] + lines


    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass 
        