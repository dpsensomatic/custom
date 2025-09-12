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

    # Campos de liquidación
    service_bonus = fields.Float(string="Prima de Servicios")
    severance = fields.Float(string="Cesantías")
    interest_on_severance = fields.Float(string="Intereses sobre Cesantías")
    vacations = fields.Float(string="Vacaciones")
    total_provisions = fields.Float(string="Total Provisiones")

    # Campo genérico por si quieres manejar valores adicionales
    amount = fields.Float(string="Valor")