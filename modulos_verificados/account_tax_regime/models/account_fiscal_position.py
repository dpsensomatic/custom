from odoo import fields,models


class AccountFiscalPosition(models.Model):
    _inherit= 'account.fiscal.position'
    
    # Fields
    account_map_ids = fields.One2many(
        "account.fiscal.position.account",
        "position_id",
        string="Mapeo de cuentas"
    )

    tax_map_ids = fields.One2many(
        "account.fiscal.position.tax",
        "position_id",
        string="Mapeo de impuestos"
    )