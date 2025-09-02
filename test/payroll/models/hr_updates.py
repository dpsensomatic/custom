from odoo import models, fields

class HrUpdates(models.Model):
    _name = 'hr.updates'
    _description = 'Novedades de Nómina'

    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    type = fields.Selection([
        ('incapacidad_eps', 'Incapacidad por EPS'),
        ('incapacidad_arl', 'Incapacidad por ARL'),
        ('permiso_remunerado', 'Permiso remunerado'),
        ('permiso_no_remunerado', 'Permiso no remunerado'),
        ('licencia_parental', 'Licencia maternidad/paternidad'),
        ('sancion', 'Sanción'),
    ], string="Tipo de novedad", required=True)

    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin")
    value_type = fields.Selection([('fixed', 'Valor fijo'), ('percent', 'Porcentaje')],
                                  string="Tipo de valor", default='fixed')
    value = fields.Float(string="Valor")
    state = fields.Selection([
        ('open', 'Activo'),
        ('closed', 'Cerrado'),
    ], string="Estado", default='open')
