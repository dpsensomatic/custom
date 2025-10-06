from odoo import fields, models


class HrContract(models.Model):
    # ==========================
    # Descripcion Del Modelo
    # ==========================
    _inherit = 'hr.contract'
    # ==========================

    # ==========================
    # Campos Del Modelo
    # ==========================
    compensation_box = fields.Boolean(string='Caja de compensación', required=True)
    arl_fee = fields.Selection([
        ('i', 'I 0.522%'),
        ('ii', 'II 1.044%'),
        ('iii', 'III 2.436%'),
        ('iv', 'IV 4.350%'),
        ('v', 'V 6.960%'),
    ], string='Tarifa ARL', default='i', required=True)
    # ==========================
    
    
    # ==========================
    # Helper
    # ==========================
    def _assign_arl(contract):
        
        arl_fee_map = {
            'i': 0.522,
            'ii': 1.044,
            'iii': 2.436,
            'iv': 4.350,
            'v': 6.960,
        }
        arl_fee_value = arl_fee_map.get(contract.arl_fee, 0.0)
        arl_fee_value /= 100
        return arl_fee_value
    
    # ==========================
    
