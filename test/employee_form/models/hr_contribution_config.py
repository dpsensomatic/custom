from odoo import models,fields,api


class EmployeeForm(models.Model):
    _name = 'hr.contribution.config'
    _description= 'Configuration for all the contribution accounts'
    
    name = fields.Char(string="Tipo de seguridad social",
                       compute = '_compute_name',
                       store = True)
    
    contribution_type = fields.Selection([
        ('eps', 'EPS'),
        ('pension', 'Fondo de Pensiones'),
        ('caja', 'Caja de Compensación'),
        ('arl', 'ARL'),
        ('solidaridad', 'Fondo de Solidaridad')
    ], string="Tipo de Aporte", required=True)
 
    account_id = fields.Many2one(
        'account.account',
        string="Cuenta Contable",
        required=True
    )
    @api.depends('contribution_type')
    def _compute_name(self):
        for record in self:
            record.name = dict(self._fields['contribution_type'].selection).get(record.contribution_type, "")
            