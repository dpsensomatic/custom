from odoo import fields,models

class ResPartner(models.Model):
    _inherit="res.partner"
    
    expedition_place = fields.Char(string='Lugar de expedicion')