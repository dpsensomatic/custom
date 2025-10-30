from odoo import models, fields

class HrEpsEntity(models.Model):
    _name = 'hr.eps.entity'
    _description = 'Entidad de Salud (EPS)'

    name = fields.Char(string='Nombre de la EPS', required=True)
    code = fields.Char(string='Código', help='Código interno o del ministerio')
    phone = fields.Char(string='Teléfono')
    address = fields.Char(string='Dirección')
    eps_account = fields.Many2one("account.account", string="Cuenta de Eps")
    active = fields.Boolean(default=True)


class HrArlEntity(models.Model):
    _name = 'hr.arl.entity'
    _description = 'Arl'

    name = fields.Char(string='Nombre del ARL', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)
    phone = fields.Char(string='Teléfono')
    arl_account = fields.Many2one("account.account", string="Cuenta de Arl")
    address = fields.Char(string='Dirección')
    
    
class HrPensionFund(models.Model):
    _name = 'hr.pension.fund'
    _description = 'Fondo de Pensión'

    name = fields.Char(string='Nombre del Fondo', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)
    phone = fields.Char(string='Teléfono')
    pension_account = fields.Many2one("account.account", string="Cuenta de pension")
    address = fields.Char(string='Dirección')
    

class HrCompensationFund(models.Model):
    _name = 'hr.compensation.fund'
    _description = 'Caja de Compensación'

    name = fields.Char(string='Nombre de la Caja', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)
    phone = fields.Char(string='Teléfono')
    compensation_account = fields.Many2one("account.account", string="Cuenta de caja de compensacion")
    address = fields.Char(string='Dirección')