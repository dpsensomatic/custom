from odoo import fields,models


class ResCompany(models.Model):
    _inherit ='res.company'
    
    transportation_allowance = fields.Monetary(
        string='Valor Auxilio de Transporte',
        currency_field='currency_id'
    )