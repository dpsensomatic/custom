from odoo import fields,models


class TaxRegime(models.Model):
    _name = "x.tax.regime"
    _description = "Add all the regimen types and his taxes"
    
    name= fields.Char(required=True)
    code= fields.Selection([
        ("gca","Gran Contribuidor Autorretenedor"),
        ("gc","Gran Contribuidor"),
        ("pja","Persona Juridica Autorretenedor"),
        ], required=True, index=True)
    tax_ids = fields.Many2many("account.tax", string="Impuestos a añadir por cada regimen")
    active = fields.Boolean(default=True)
    
    