from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date
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
    def _empty_totals(self, concept):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return {                 
            'concept': concept,
            'start_date': 0.0,
            'end_date': 0.0,
            'period_days': 0.0,
            'contract_wage':0.0,
            'incapacity_days': 0.0,
            'transport_days':0.0,
            'transport_value':0.0,
            'commissions_value':0.0,
            'absences': 0.0,
            'settlement_days': 0.0,
            'average_wage': 0.0,
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
        
        # ========================
        # Trae Los eventos 
        # ========================
        # === Filtra Lo Eventos Y Trae Los Existententes Dentro Del Periodo ===
        if concept == 'prima':
            start_date_prima = date(2025,7,1)
            if start_date_prima > self.cutoff_date:
                events = self.env["hr.payroll.mixin"]._get_events(self.employee_id.id, self.contract_start_date, self.cutoff_date)
            elif start_date_prima >= self.contract_start_date:
                events = self.env["hr.payroll.mixin"]._get_events(self.employee_id.id, start_date_prima, self.cutoff_date)
            else:
                d1 = fields.Date.from_string(self.contract_start_date)
                p1 = fields.Date.from_string(start_date_prima)
                overlap_start = max(p1, d1)
                events = self.env["hr.payroll.mixin"]._get_events(self.employee_id.id, overlap_start, self.cutoff_date)
                
        else:
            events = self.env["hr.payroll.mixin"]._get_events(self.employee_id.id, self.contract_start_date, self.cutoff_date)
            
        # === Se Guardan Los Eventos Que Se Comportan Distinto ===
        incapacity_types = ['sick_leave', 'paid_leav', 'arl_leave']
        unpaid_events = events.filtered(lambda e: e.type == 'unpaid_leave')
        incapacity_events = events.filtered(lambda e: e.type in incapacity_types)
        commissions_events = events.filtered(lambda e: e.type == 'commissions')
        # ========================

        # === Inicializa El Diccionario ===
        totals = self._empty_totals(concept)
                
        # === Trae El Sueldo Del Contrato ===
        totals['contract_wage'] = self.employee_id.contract_id.wage
        
        # === Trae Los Dias De Ausencia Con Las Licencias No Remuneradas ===
        totals = self.env["hr.payroll.mixin"]._compute_settlement_days(concept, unpaid_events, self.contract_start_date, self.cutoff_date, totals)

        # ========================
        # Calculo auxilio de transporte
        # ========================
        # === Trae El Valor De Auxilio De Transporte Y Lo Ajusta A Valor Por Dia===
        parameters = self.env['hr.payroll.mixin']._get_parameter(self.contract_id.date_start)
        transport_day_value = parameters['transport_allowance']/30
        
        # === Recorre Los Eventos Que Descuentan EL Auxilio De Transporte ===
        for event in incapacity_events:
            totals['incapacity_days'] += event.quantity
        for event in unpaid_events:
            totals['incapacity_days'] += event.quantity
            totals['absences'] += event.quantity
        totals['transport_days'] = totals['period_days'] - totals['incapacity_days']
        
        # === Ajusta El Valor Total Del Auxilio De Transporte ===
        totals['transport_value'] = totals['transport_days'] * transport_day_value  
        # ========================
        
           
        # === Se Ajusta El Total De Dias A Liquidar ===
        totals['settlement_days'] = totals['period_days'] - totals['absences']

        for commission in commissions_events:
            totals['commissions_value'] += commission.fixed_value
        
        totals = self.env['hr.payroll.mixin']._compute_settlement_totals(totals,
                                                                         totals['contract_wage'], 
                                                                         totals['settlement_days'],
                                                                         totals['commissions_value'],
                                                                         totals['transport_value'],
                                                                         totals['absences'],
                                                                         concept
                                                                         )
        
        # === Calculo De Los Conceptos A Liquidar ===
        totals = self.env['hr.payroll.mixin']._calculate_liquidated_wage(concept, totals)
        
        return {
            'concept': concept.replace('_', ' ').title(),
            'start_date': self.employee_id.contract_id.date_start,
            'end_date': self.cutoff_date,
            'period_days': totals['period_days'],
            'absences': totals['absences'],
            'settlement_days': totals['settlement_days'],
            'average_wage': totals['average_wage'],
            'value_wage': totals['value_wage'],
            'advances': totals['advances'],
            'net_value': totals['net_value'],
        }
    # ========================
# ========================    