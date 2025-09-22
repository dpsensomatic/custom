from odoo import models, fields

class AccountTax(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(
        selection_add=[('base', 'Porcentaje sobre monto base mínimo')],
        ondelete={'base': 'set default'}
    )
    minimum_base_amount = fields.Monetary(
        string="Base mínima",
        currency_field='company_currency_id',
        help="Si la base imponible es menor a este valor, el impuesto no se aplicará."
    )
    is_tax_on_vat = fields.Boolean(
        string="Aplica Sobre el IVA?",
        help="Si está marcado, el impuesto se aplicará sobre la suma del IVA del documento."
    )
    is_retention = fields.Boolean(
        string="Es retención",
        default=False,
        help="Si está marcado, el impuesto se considera una retención: se registra contablemente pero no afecta el total visible de la factura."
    )

    # company currency helper if you need
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Currency (company)",
        store=True,
        readonly=True,
    )
