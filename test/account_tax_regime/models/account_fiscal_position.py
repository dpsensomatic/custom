from odoo import models,fields

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    invoice_level_tax_ids = fields.Many2many(
        'account.tax', 'fpos_invoice_level_tax_rel', 'position_id', 'tax_id',
        string="Impuestos nivel factura por posición",
    )    