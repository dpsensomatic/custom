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
        help='Se debe crear el aporte a eps'
        
    )
    eps_affiliation_date = fields.Date(
        string='Fecha de afiliación EPS'
    )
    
    pension_fund_id = fields.Many2one(
        'hr.pension.fund',
        string='Fondo de Pensión',
        help='Se debe crear el aporte a pension'
    )
    pension_affiliation_date = fields.Date(
        string='Fecha de afiliación Pensión'
    )
    
    arl_id= fields.Many2one(
        'hr.arl.entity',
        string='ARL',
        help='Se debe crear el aporte de arl'
    )
    arl_affiliation_date = fields.Date(
        string='Fecha de afiliación ARL'
    )
    
    # === Caja de compensacion ===
    compensation_check = fields.Boolean(string='Caja de compensación')
    compensation_fund_id = fields.Many2one(
        'hr.compensation.fund',
        string='Entidad caja de compensación',
        help='Se debe crear el aporte a caja de compensacion'
    )
    compensation_affiliation_date = fields.Date(
        string='Fecha de afiliación Caja de Compensación'
    )
    
    
    # === Tipo De Vinculacion ===
    sena_apprentice = fields.Boolean(string='Aprendiz Sena')
    apprentice_type = fields.Selection([
        ('academic','Etapa Lectiva'),
        ('productive','Etapa Productiva')
    ], string='Etapa del aprendiz')
    
    intern = fields.Boolean(string='Pasante')
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