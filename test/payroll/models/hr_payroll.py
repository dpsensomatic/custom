# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb
import logging


_logger = logging.getLogger(__name__)

# ========================
# Definicion Del Modelo
# ========================
class HrPayroll(models.Model):
    
    # === Descripcion Del Modelo ===
    _name = "hr.payroll"
    _description = "Nómina"

    # === Campos del Modelo ===
    name = fields.Char(string="Nombre", required=True, default="Nómina")
    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin", required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Cerrada'),
    ], string="Estado", default="draft")

    # === Campos Many ===
    line_ids = fields.One2many("hr.payroll.line", "payroll_id", string="Líneas de nómina")
    # ========================
    
    
    # ========================
    # Helpers pequeños
    # ========================
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return { 
                # === Datos Del Empleado Y Contrato ===
                'employee_id':0.0,
                'contract_id': 0.0,
                'base_wage': 0.0,
                
                # === Salario Ajustado Por Las Novedades ===
                'wage_earned': 0.0,
                'days_worked': 0.0,
                'unpaid_days': 0.0,
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'transportation_allowance': 0.0,
                'night_surcharge': 0.0,
                'other':0.0,
                'gross': 0.0,
                
                # === Aportes A Seguridad Social ===
                'health_contribution':0.0,
                'pension_contribution':0.0,
                'company_health_contribution':0.0,
                'company_pension_contribution':0.0,
                'arl_contribution':0.0,
                'other_deductions':0.0,
                
                'deductions':0.0,
                'total_deductions':0.0,
                
                # === Pagos A Prestaciones Sociales ===
                'service_bonus':0.0,
                'severance':0.0,
                'interest_on_severance':0.0,
                'vacations':0.0,
                'total_provisions':0.0,
                
                # === Totales A Pagar ===
                # Pago Empleado
                'net':0.0,
                # Pago Empresa
                'total_net':0.0,
        }

    # ========================
    # Acción principal (Genera Las Lineas De La Nomina)
    # ========================
    def action_generate_lines(self):
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
        
        # === Trae Todos Los Empleado Creados En Hr_Employee ===
        employees = self.env['hr.payroll.mixin']._get_employees_with_contracts(self.date_start, self.date_end)
        lines = []

        # === Hace El Bucle De los Empleados Y Sus Respectivos Contratos ===
        for employee, contract in employees.items():

            # === Trae Los Eventos Por Empleado Segun Fecha De La Nomina ===
            events = self.env['hr.payroll.mixin']._get_events(employee.id, self.date_start, self.date_end)
            parameters = self.env['hr.payroll.mixin']._get_parameter(self.date_start)

            # === Ajustamos los parametros  ===
            transportation_allowance = parameters['transport_allowance']
            company_pension_percentage = parameters['company_pension_percentage']
            company_health_percentage = parameters['company_eps_percentage']
            employee_eps_percentage = parameters['employee_eps_percentage']
            employee_pension_percentage = parameters['employee_pension_percentage']
            minimun_wage = parameters['minimum_wage']

            # === Vacia Los Totales Del Diccionario Con Cada Ciclo ===            
            totals = self._empty_totals()

            # === Calculo De Los Dias Trabajados ===
            totals = self.env['hr.payroll.mixin']._compute_days_worked(events, totals,  self.date_start, self.date_end)

            # === Calculo del Salario segun incapacidades ===
            totals['wage_earned'] = contract.wage * (totals['days_worked'] / 30)

            # === Calculo Auxilio De Transporte ===
            totals['transportation_allowance'] = self.env['hr.payroll.mixin']._compute_transport_allowance(
                totals['wage_earned'], totals['days_worked'], minimun_wage, transportation_allowance
            )

            # === Total A Pagar Al Trabajador ===
            totals['gross'] = self.env['hr.payroll.mixin']._compute_total_gross(totals)

            # === Aportes A Seguridad Social (Salud, Pension, ARL) ===
            totals = self.env['hr.payroll.mixin']._compute_contributions(
                totals,
                company_health_percentage,
                employee_eps_percentage,
                company_pension_percentage,
                employee_pension_percentage,
                minimun_wage,
                contract,
            )

            # === Aportes A Prestaciones Sociales (Prima, Cesantias, Vacaciones) ===
            totals = self.env['hr.payroll.mixin']._compute_benefits( totals)

            # === Totales De Aportes A Seguridad Social (Salud, Pension, ARL) ===
            # Total A Pagar Trabajador
            totals['deductions'] = totals['health_contribution'] + totals['pension_contribution']

            # Total A Pagar Empleador
            totals['total_deductions'] = totals['deductions'] + totals['arl_contribution']

            # ========================


            # ========================
            # Crea Las Lineas Con La Informacion Recolectada
            # ========================
            vals_line = {
                # === Datos Del Empleado Y Contrato ===
                'employee_id': employee.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,

                # === Salario Ajustado Por Las Novedades ===
                'wage_earned': totals['wage_earned'],
                'days_worked': totals['days_worked'],
                'sick_leave': totals['sick_leave'],
                'overtime_hours': totals['overtime_hours'],
                'transportation_allowance': totals['transportation_allowance'],
                'night_surcharge': totals['night_surcharge'],
                'other': totals['other'],
                'gross': totals['gross'],

                # === Aportes A Seguridad Social ===
                'health_contribution': totals['health_contribution'],
                'pension_contribution': totals['pension_contribution'],
                'company_health_contribution': totals['company_health_contribution'],
                'company_pension_contribution': totals['company_pension_contribution'],
                'arl_contribution': totals['arl_contribution'],
                'other_deductions': 0.0,

                'deductions': totals['deductions'],
                'total_deductions': totals['total_deductions'],

                # === Pagos A Prestaciones Sociales ===
                'service_bonus': totals['service_bonus'],
                'severance': totals['severance'],
                'interest_on_severance': totals['interest_on_severance'],
                'vacations': totals['vacations'],
                'total_provisions': totals['total_provisions'],

                # === Totales A Pagar ===
                # Pago Empleado
                'net': totals['gross'] - totals['deductions'],
                # Pago Empresa
                'total_net': totals['gross'] + totals['total_deductions'],
            }

            # ===  ===
            lines.append((0, 0, vals_line))

        # ===  ===
        self.line_ids = [(5, 0, 0)] + lines

    # ========================

    # ========================
    # Genera Los Apuntes Contables
    # ========================
    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass 
    # ========================