from odoo import fields, models

class HrPayrollSettlementLine(models.Model):
    _name = "hr.payroll.settlement.line"
    _description = "Línea De Prima De Servicios"

    date = fields.Date()
    concept = fields.Char()
    value = fields.Float()
    origin = fields.Char()
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)
    
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", required=True)
    service_bonus = fields.Many2one('hr.service.bonus', string="Prima", ondelete='cascade')