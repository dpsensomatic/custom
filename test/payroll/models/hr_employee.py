from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    expedition_place = fields.Char(string="Expedition Place")
    sena_type = fields.Selection([
        ('apprentice', 'Lectiva'),
        ('graduate', 'Productiva'),
    ], string="SENA Type")
    cotizante_type = fields.Many2one(
        "hr.cotizante.type", string="Tipo de Cotizante")
    contract_type = fields.Many2one("hr.contract.type", string="Contract Type")
