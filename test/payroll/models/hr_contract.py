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
    arl_fee = fields.Selection([
        ('i', 'I 0.522%'),
        ('ii', 'II 1.044%'),
        ('iii', 'III 2.436%'),
        ('iv', 'IV 4.350%'),
        ('v', 'V 6.960%'),
    ], string='Tarifa ARL', default='i', required=True)
    
    # === Aportes ===
    eps_id = fields.Many2one(
        'hr.eps.entity',
        string='EPS',
        help='Entidad promotora de salud del empleado'
    )
    pension_fund_id = fields.Many2one(
        'hr.pension.fund',
        string='Fondo de Pensión'
    )
    arl_id= fields.Many2one(
        'hr.arl.entity',
        string='ARL',
        help='Entidad promotora de seguridad del empleado'
    )
    
    # === Caja de compensacion ===
    compensation_check = fields.Boolean(string='Caja de compensación')
    compensation_fund_id = fields.Many2one(
        'hr.compensation.fund',
        string='Entidad caja de compensación'
    )
    
    
    # === Tipo De Vinculacion ===
    sena_apprentice = fields.Boolean(string='Aprendiz Sena')
    apprentice_type = fields.Selection([
        ('academic','Etapa Lectiva'),
        ('productive','Etapa Productiva')
    ], string='Etapa del aprendiz')
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
    

