from odoo import fields, models

class HrPayrollLine(models.Model):
    _name = "hr.payroll.line"
    _description = "Payroll Line"

    # Información general
    payroll_id = fields.Many2one("hr.payroll", string="Payroll", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato")

    # Datos base del trabajador 
    base_wage = fields.Float(string="Salario Base")
    wage_earned = fields.Float(string='Salario Ajustado')
    days_worked = fields.Float(string="Dias Trabajados")
    transportation_allowance = fields.Float(string="Transporte")

    # Devengados (ingresos adicionales)
    sick_leave = fields.Float(string="Incapacidad")  # valor por incapacidad
    overtime_hours = fields.Float(string="Horas Extras")  # horas extras
    night_surcharge = fields.Float(string="Recargo Nocturno")  # recargo nocturno
    other_earnings = fields.Float(string="Otros devengados")  # otros ingresos
    gross = fields.Float(string="Total Devengados", compute="_compute_totals", store=True)

    # Deducciones
    health_contribution = fields.Float(string="Aportes Salud")
    pension_contribution = fields.Float(string="Aportes Pension")
    other_deductions = fields.Float(string="Otras Deducciones")
    deductions = fields.Float(string="Deducciones", compute="_compute_totals", store=True)

    # Total a pagar
    net = fields.Float(string="Neto a Pagar", compute="_compute_totals", store=True)


