from odoo import models, fields

class HrBonusBenefits(models.Model):
    _name = 'hr.accrued'
    _description = 'Devengados'

    name = fields.Char(string="Nombre", required=True)
    account_id = fields.Many2one('account.account', string="Cuenta contable", required=True)
    amount = fields.Float(string="Monto")
    value_type = fields.Selection([
        ('fixed', 'Valor fijo'), 
        ('percent', 'Porcentaje')
        ], string="Tipo de valor", default='percent')
    active = fields.Boolean(default=True) 
