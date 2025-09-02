from odoo import models, fields

class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    code = fields.Char(string="Código", index=True)
