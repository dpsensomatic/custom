# -*- coding: utf-8 -*-
from odoo import models, fields

class HrContract(models.Model):
    _inherit = 'hr.contract'

    transportation_allowance = fields.Boolean( string='Aplica Auxilio de transporte')
    
    