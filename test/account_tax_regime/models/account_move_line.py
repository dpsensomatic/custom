from odoo import models, api, fields
import logging
import ipdb

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        res = super()._get_computed_taxes()
        # si super ya devolvió una lista de taxes, filtramos out is_invoice_level
        if res:
            res = res.filtered(lambda t: not t.is_invoice_level)
        return res