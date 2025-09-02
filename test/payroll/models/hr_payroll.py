# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import ipdb 
import logging

_logger = logging.getLogger(__name__)

class HrPayroll(models.Model):
    # Definicion del modelo
    _name = "hr.payroll"
    _description = "Nómina"

    # Campos del modelo
    name = fields.Char(string="Nombre", required=True, default="Nómina")
    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin", required=True)
    line_ids = fields.One2many("hr.payroll.line", "payroll_id", string="Líneas de nómina")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Cerrada'),
    ], string="Estado", default="draft")

    def action_generate_lines(self):
        """Genera automáticamente una línea de nómina consolidada por empleado"""
        self.ensure_one()

        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")

        employees = self.env['hr.employee'].search([('contract_id.state', '=', 'open')])
        lines = []

        for emp in employees:
            contract = emp.contract_id
            if not contract:
                continue

            # Auxilio de Transporte
            if contract.transportation_allowance == True:
                allow_value = contract.company_id.transportation_allowance
            else:
                allow_value = 0
            # Buscar eventos del empleado en el periodo
            events = self.env['hr.payroll.events'].search([
                ('employee_id', '=', emp.id),
                ('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
            ])

            # Consolidar valores
            comissions = 0.0
            total_gross = 0.0
            total_deductions = 0.0
            extra_hours = 0.0
            night_surcharge = 0.0
            sick_leave = 0.0
            arl_leave = 0.0
            unpaid_days = 0  # aquí acumulamos los días no trabajados

            salario_mensual = contract.wage
            valor_dia = salario_mensual / 30

            for ev in events:
                vals = ev.compute_value()
                comissions += vals.get('comissions', 0.0)
                arl_leave += vals.get('arl', 0.0)  
                sick_leave += vals.get('sick', 0.0)  
                extra_hours += vals.get('extra_hours', 0.0)
                night_surcharge += vals.get('night_surcharge', 0.0)
                # total_gross += vals.get('gross', 0.0)
                total_deductions += vals.get('deductions', 0.0)
                            # Si es incapacidad o licencia no remunerada, descuentan días al salario

                if ev.type in ['sick_leave', 'arl_leave','unpaid_leave']:
                    unpaid_days += ev.quantity

            # Ajustar salario por días trabajados
            days_worked = 30 - unpaid_days
            base_wage = valor_dia * days_worked
                
            total_gross = base_wage + sick_leave + arl_leave + extra_hours + allow_value + night_surcharge + comissions
            # Crear **una sola línea** con totales
            lines.append((0, 0, {
                'employee_id': emp.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,
                'wage_earned': base_wage,
                'days_worked': days_worked, 
                'sick_leave':sick_leave + arl_leave,
                'overtime_hours': extra_hours,
                'transportation_allowance': allow_value,  # Falta por ajustar a los días trabajados
                'night_surcharge': night_surcharge,
                'other_earnings':comissions,
                'gross': total_gross,
                'health_contribution': 0,
                'pension_contribution': 0,
                'other_deductions':0,
                'deductions': total_deductions,
                'net': total_gross - total_deductions,   
            }))
            # ipdb.set_trace()

        # Limpiar y asignar las líneas
        self.line_ids = [(5, 0, 0)] + lines

            


    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass