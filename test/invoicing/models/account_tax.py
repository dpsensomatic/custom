from odoo import models, fields, api


class AccountTax (models.Model):
    # ===
    _inherit = 'account.tax'
    
    # === Definicion De Los Campos ===
    minimum_base_amount = fields.Float(string="Monto base mínimo")
        
    
    