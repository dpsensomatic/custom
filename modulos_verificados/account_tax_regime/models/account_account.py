from odoo import fields,models

class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    # parent_account_id= fields.Many2one('account.account', string='Subcuenta de:')
    # is_inactive= fields.Boolean(string='¿Esta inactiva?')
    # is_hidden= fields.Boolean(string='ocultar')
    # axi_code= fields.Char(string='Codigo AXI')
    # is_postable= fields.Boolean(string='contabilizacion')
    requires_partner= fields.Boolean(string='requiere terceros')