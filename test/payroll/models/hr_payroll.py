# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb
import logging


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
                'unpaid_days': 0.0,
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'transportation_allowance': 0.0,
                'night_surcharge': 0.0,
                'other':0.0,
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

        # ========================
        # Verifica que se hayan elegido las fechas de nomina
        # ========================
        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")
        # ========================
        
        # ========================
        # Trae Todos los empleados con sus contratos
        # ========================
        # ===  ===
        employees = self.env['hr.payroll.mixin']._get_employees_with_contracts(self.date_start, self.date_end)
        lines = []

        # ===  ===
        for employee, contract in employees.items():
            # === Trae Los Eventos Por Empleado Segun Fecha De La Nomina ===
            events = self.env['hr.payroll.mixin']._get_events(employee.id, self.date_start, self.date_end)
            parameters = self.env['hr.payroll.mixin']._get_parameter(self.date_start)

            # ===  ===
            transportation_allowance = parameters['transport_allowance']
            company_pension_percentage = parameters['company_pension_percentage']
            company_health_percentage = parameters['company_eps_percentage']
            employee_eps_percentage = parameters['employee_eps_percentage']
            employee_pension_percentage = parameters['employee_pension_percentage']
            minimun_wage = parameters['minimum_wage']
            arl_fee = parameters['arl_fee']
    
            # ===  ===
            expected = 30
            totals = self._empty_totals()
            totals = self.env['hr.payroll.mixin']._compute_days_worked(events, totals,  self.date_start, self.date_end)
            
            # ===  ===
            wage_earned = (contract.wage * (totals['days_worked'] / expected)) if expected else 0.0
            
            # ===  ===
            allow_value = self.env['hr.payroll.mixin']._compute_transport_allowance(
                wage_earned, totals['days_worked'], minimun_wage, transportation_allowance
            )
    
            # === Total A Pagar Al Empleador ===
            total_gross = (
                wage_earned +
                totals['sick_leave'] +
                totals['overtime_hours'] +
                totals['night_surcharge'] +
                totals['other'] +
                allow_value
            )
    
            # ===  ===
            benefits = self.env['hr.payroll.mixin']._compute_benefits(total_gross, wage_earned, totals['days_worked'])

            # ===  ===
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
    
            # ===  ===
            health_contributions = contributions['employee_eps']
            pension_contributions = contributions['employee_pension']
            company_health_contribution = contributions['company_eps']
            company_pension_contribution = contributions['company_pension']
            arl_fee_value = contributions['arl_contribution']

            # ===  ===
            total_deductions_employee = health_contributions + pension_contributions
            total_deductions = total_deductions_employee + arl_fee_value

            # ===  ===
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
            
            # ========================
            # 
            # ========================
            vals_line = {
                # === Datos Del Empleado Y Contrato ===
                'employee_id': employee.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,
                
                # === Salario Ajustado Por Las Novedades ===
                'wage_earned': wage_earned,
                'days_worked': totals['days_worked'],
                'sick_leave': totals['sick_leave'],
                'overtime_hours': totals['overtime_hours'],
                'transportation_allowance': allow_value,
                'night_surcharge': totals['night_surcharge'],
                'other': totals['other'],
                'gross': total_gross,
                
                # === Aportes A Seguridad Social ===
                'health_contribution': health_contributions,
                'pension_contribution': pension_contributions,
                'company_health_contribution': company_health_contribution,
                'company_pension_contribution': company_pension_contribution,
                'arl_contribution': arl_fee_value,
                'other_deductions': 0.0,
                'deductions': total_deductions_employee,
                'total_deductions': total_deductions,
                
                # === Pagos A Prestaciones Sociales ===
                'service_bonus': totals['service_bonus'],
                'severance': totals['severance'],
                'interest_on_severance': totals['interest_on_severance'],
                'vacations': totals['vacations'],
                'total_provisions': totals['total_provisions'],
                
                # === Totales A Pagar ===
                # Pago Empleado
                'net': total_gross - total_deductions,
                # Pago Empresa
                'total_net': total_gross - total_deductions,
            }
            # ========================
            
            # ===  ===
            lines.append((0, 0, vals_line))

        # ===  ===
        self.line_ids = [(5, 0, 0)] + lines
        
    # ========================
    #
    # ========================
    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass 
    # ========================