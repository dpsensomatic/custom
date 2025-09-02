from odoo import models,fields


class HrContract(models.Model):
    _inherit= 'hr.contract'
    
    contract_class = fields.Selection([
        ('normal','Normal'),
        ('sena','Aprendiz Sena'),
        ('min','Salario Inferior Al Minimo'),
        ('integral','Salario Integral')
    ],  string='Clase del contrato',
        default='normal',
        required=True
    )
    