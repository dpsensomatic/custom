from odoo import fields, models

class HrPayrollSettlementLine(models.Model):
    _name = "hr.payroll.settlement.line"
    _description = "Línea de Liquidación"

    settlement_id = fields.Many2one(
        "hr.payroll.settlement",
        string="Liquidación",
        required=True,
        ondelete="cascade"
    )

    name = fields.Char(string="Concepto")
    amount = fields.Float(string="Valor")