from odoo import fields,models

class HrContributionAccounts(models.Model):
    _name= 'hr.contribution.accounts'
    _description= 'Model to add all the information about contribution accounts '
    
    # Campos 
    type = fields.Selection([
        ('eps', 'EPS'),
        ('arl', 'ARL'),
        ('pension', 'Fondo de Pension'),
        ('compensation', 'Caja de compensacion'),
        ('other', 'Otros'),
    ], string='Tipos de Aportes', required=True)
    
    name=fields.Char(string='Nombre de la Cuenta', required=True)
    account_id = fields.Many2one('account.account', string="Cuenta contable", required=True)
    value_type = fields.Selection([
        ('fixed', 'Valor fijo'), 
        ('percent', 'Porcentaje')
        ], string="Tipo de valor", default='percent')
    value = fields.Float(string="Valor", help="Puede ser monto fijo o porcentaje")
    active = fields.Boolean(string="Activo", default=True)
    

    
    
    