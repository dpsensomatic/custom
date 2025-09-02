from odoo import fields,models


class HrEmployee(models.Model):
    _inherit="hr.employee"    

    expedition_place = fields.Char(
        related="address_id.expedition_place",
        store=True,
        readonly=False  # Para que sea editable directamente en empleado
    )

    l10n_latam_identification_type_id = fields.Many2one(
        'l10n_latam.identification.type',
        related="address_id.l10n_latam_identification_type_id",
        string="Tipo de Identificación",
        store=True,
        readonly=False
    )
    

    