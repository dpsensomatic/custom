from odoo import fields, models, api
from odoo.exceptions import UserError
import ipdb

# ========================
# Definicion Del Modelo
# ========================
class HrPayrollSettlement(models.Model):
    
    # === Descripcion Del Modelo ===
    _name = 'hr.payroll.settlement'
    _description = 'Liquidación de Nómina'

    # === Campos Del Modelo (No Computados) ===
    name = fields.Char(string="Nombre de la liquidacion", required=True)
    termination_reason = fields.Char(string="Causa de retiro ")
    creation_date = fields.Date(string="Fecha de creacion de la liquidacion")
    cutoff_date = fields.Date(string="Fecha de corte de la liquidacion", required=True)
    
    # === Campos Del Modelo (Computados) === 
    identification_number = fields.Char(string="Numero de identificacion", compute='_compute_contract_fields', store=True)
    contract_type = fields.Char(string="Tipo de contrato", compute='_compute_contract_fields', store=True)
    contract_start_date = fields.Date(string="Fecha inicio contrato", compute='_compute_contract_fields', store=True)
    contract_end_date = fields.Date(string="Fecha fin contrato", compute='_compute_contract_fields', store=True)
    job_position = fields.Char(string="Cargo", compute='_compute_contract_fields', store=True)
    
    # === Estado :3 ===
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)
    
    # === Campos Many ===
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", required=True)
    line_ids = fields.One2many("hr.payroll.settlement.line", "liquidation_id", string="Líneas de Liquidación")

    
    
# ========================
# Campos Computados
# ========================
    # ========================
    # Computa Los Campos Del Contrato
    # ========================
    @api.depends('employee_id')
    def _compute_contract_fields(self):
        for record in self:
            employee = record.employee_id
            contract = employee.contract_id if employee else False
            record.contract_id = contract
            record.contract_start_date = contract.date_start if contract else False
            record.contract_end_date = contract.date_end if contract else False
            record.identification_number = employee.identification_id if employee else False
            record.contract_type = contract.contract_type_id.name if contract and contract.contract_type_id else False
            record.job_position = contract.job_id.name if contract and contract.job_id else False
    # ========================
# ========================


# ========================
# Helpers Pequeños
# ========================
    # ========================
    #  Vacia Los Totales Que Hayan En Los Diccionarios
    # ========================
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return {                 
            'concept': 0.0,
            'start_date': 0.0,
            'end_date': 0.0,
            'days_period': 0.0,
            'contract_wage':0.0,
            'incapacity_days': 0.0,
            'absences': 0.0,
            'days_settlement': 0.0,
            'average_wage': 0.0,
            'base_wage': 0.0,
            'value_wage': 0.0,
            'advances': 0.0,
            'net_value': 0.0,
        }
    # ========================
# ========================


# ========================
# Acciones Principales
# ========================
    # ========================
    # Genera Las Lineas De La Liquidacion
    # ========================
    def action_generate_settlement_lines(self):

        # === Se Crea El Diccionario Vacio Y Se Crean Los Conceptos Para Generar Las Lineas ===
        lines = []
        concepts = ['prima', 'cesantias', 'intereses_cesantias', 'vacaciones']

        # === ===
        for concept in concepts:
            vals_line = self._get_line_vals(concept)
            if vals_line:
                lines.append((0, 0, vals_line))
                
        # === ===
        self.line_ids = [(5, 0, 0)] + lines
    # ========================


    # ========================
    # Devuelve La Informacion De Las Lineas
    # ========================
    def _get_line_vals(self, concept):
        
        # === Trae Los Eventos Y Filtra Los De Tipo 'unpaid_leave' ===
        events = self.env["hr.payroll.mixin"]._get_events(self.employee_id.id, self.contract_start_date, self.cutoff_date)
        incapacity_types = ['sick_leave', 'arl_leave']
        unpaid_events = events.filtered(lambda e: e.type == 'unpaid_leave')
        incapacity_events = events.filtered(lambda e: e.type in incapacity_types)
        commissions_events = events.filtered(lambda e: e.type == 'commissions')
        totals = self._empty_totals()

        for event in incapacity_events:
            totals['incapacity_days'] += event.quantity
            
        
        ipdb.set_trace()
        
        
        # === ===
        contract = self.employee_id.contract_id
        totals['contract_wage'] = contract.wage
        totals = self.env["hr.payroll.mixin"]._compute_settlement_days(concept, unpaid_events, self.contract_start_date, self.cutoff_date, totals)
        ipdb.set_trace()
        totals = self.env['hr.payroll.mixin']._compute_settlement_total(commissions_events, totals.days_settlement, totals.contract_wage) #Aqui se calcula salario base y salario promedio
        
        # prima = base_parafiscal + salario_transporte No tiene el rodamiento
        # vacaciones = comision + sueldo + rodamiento es lo mismo que la base parafiscal sin las horas extras
        ipdb.set_trace()
        # === Calculo De Los Conceptos A Liquidar ===
        totals = self.env['hr.payroll.mixin']._calculate_liquidated_wage(concept, totals)
        ipdb.set_trace()
        return {
            'concept': concept.replace('_', ' ').title(),
            'start_date': contract.date_start,
            'end_date': self.cutoff_date,
            'days_period': totals['days_period'],
            'absences': totals['absences'],
            'days_settlement': totals['days_settlement'],
            'average_wage': totals['average_wage'],
            'base_wage' : totals['base_wage'],
            'value_wage': totals['value_wage'],
            'advances': totals['advances'],
            'net_value': totals['net_value'],
        }
    # ========================
# ========================    