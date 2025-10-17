from odoo import models, fields, api
import ipdb

# ========================
# Definicion Del Modelo
# ========================
class HrServiceBonus(models.Model):
    _name = 'hr.service.bonus'
    _description = 'Modelo para calcular la prima de Servicios'
    
    #  === Campos Del Modelo (No Computados) ===
    bonus_date_end = fields.Date(string="Fecha de corte de la liquidacion", required=True)
    
    # === Campos Del Modelo (Computados) === 
    contract_start_date = fields.Date(string="Fecha inicio contrato", compute='_compute_contract_fields', store=True)
 
    
    days_period = fields.Float(string="Días Período")
    absences = fields.Float(string="Ausencia")
    days_settlement = fields.Float(string="Días Liq.")

    # === Estado :3 ===
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)
    
    # === Campos Many ===
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", required=True)
    line_ids = fields.One2many("hr.service.bonus.line", "service_bonus", string="Líneas de Liquidación")
    
    
    
    
    
    