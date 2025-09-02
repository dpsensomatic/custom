from odoo import models, fields

class AccountFiscalPositionAccount(models.Model):
    _inherit = "account.fiscal.position.account"

    # Campos ya existentes en Odoo:
    position_id = fields.Many2one(
        "account.fiscal.position",
        string="Posición fiscal",
        required=True,
        ondelete="cascade"
    )
    account_src_id = fields.Many2one(
        "account.account",
        string="Cuenta origen",
        required=True
    )
    account_dest_id = fields.Many2one(
        "account.account",
        string="Cuenta destino",
        required=True
    )
