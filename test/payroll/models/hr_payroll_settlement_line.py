from odoo import fields, models

class HrPayrollSettlementLine(models.Model):
    _name = "hr.payroll.settlement.line"
    _description = "Línea de Liquidación"

    liquidation_id = fields.Many2one('hr.payroll.settlement', string="Liquidación", ondelete='cascade')
    concept = fields.Char(string="Concepto")
    start_date = fields.Date(string="Fecha Inicial")
    end_date = fields.Date(string="Fecha Final")
    days_period = fields.Float(string="Días Período")
    absences = fields.Float(string="Ausencia")
    days_settlement = fields.Float(string="Días Liq.")
    average_wage = fields.Monetary(string="Salario Promedio")
    value_wage = fields.Monetary(string="Vr Líquid.")
    advances = fields.Monetary(string="Anticipos")
    net_value = fields.Monetary(string="Valor Neto")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)