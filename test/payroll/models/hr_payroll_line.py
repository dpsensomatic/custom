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
    gross = fields.Float(string="Total Devengados", store=True)

    # Deducciones
    health_contribution = fields.Float(string="Aportes Salud")
    pension_contribution = fields.Float(string="Aportes Pension")
    company_health_contribution = fields.Float(string="Aportes Salud Empresa")
    company_pension_contribution = fields.Float(string="Aportes Pension Empresa")
    arl_contribution = fields.Float(string="Aportes ARL")
    other_deductions = fields.Float(string="Otras Deducciones")
    deductions = fields.Float(string="Deducciones", store=True)
    total_deductions = fields.Float(string="Total Deducciones", store=True)
    
    #prestaciones sociales
    service_bonus = fields.Float(string="Prima", store=True)
    severance = fields.Float(string="Cesantías", store=True)
    interest_on_severance = fields.Float(string="Intereses Cesantías", store=True)
    vacations = fields.Float(string="Vacaciones", store=True)
    total_provisions = fields.Float(string="Total Prestaciones Sociales", store=True)

    # Total a pagar
    net = fields.Float(string="Neto a Pagar", store=True)
    total_net = fields.Float(string="Total Neto a Pagar", store=True)
    
    
    


