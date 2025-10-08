
# ==========================
# Modelo: Liquidación de Nómina
# ==========================
from odoo import fields, models, api
from odoo.exceptions import UserError
import ipdb

class HrPayrollSettlement(models.Model):
    _name = 'hr.payroll.settlement'
    _description = 'Liquidación de Nómina'

    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", required=True)
    line_ids = fields.One2many("hr.payroll.settlement.line", "liquidation_id", string="Líneas de Liquidación")

    name = fields.Char(string="Nombre de la liquidacion", required=True)
    settlement_creation_date = fields.Date(string="Fecha de creacion de la liquidacion")
    settlement_cutoff_date = fields.Date(string="Fecha de corte de la liquidacion")
    termination_reason = fields.Char(string="Causa de retiro ")
    employee_identification_number = fields.Char(string="Numero de identificacion", compute='_compute_contract_fields', store=True)
    contract_type = fields.Char(string="Tipo de contrato", compute='_compute_contract_fields', store=True)
    contract_start_date = fields.Date(string="Fecha inicio contrato", compute='_compute_contract_fields', store=True)
    contract_end_date = fields.Date(string="Fecha fin contrato", compute='_compute_contract_fields', store=True)
    job_position = fields.Char(string="Cargo", compute='_compute_contract_fields', store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)

    # ========================
    # Helpers pequeños
    # ========================
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return {                 
            'concept': 0.0,
            'start_date': 0.0,
            'end_date': 0.0,
            'days_period': 0.0,
            'absences': 0.0,
            'days_settlement': 0.0,
            'average_wage': 0.0,
            'value_wage': 0.0,
            'advances': 0.0,
            'net_value': 0.0,
        }

    @api.depends('employee_id')
    def _compute_contract_fields(self):
        for record in self:
            employee = record.employee_id
            contract = employee.contract_id if employee else False
            record.contract_id = contract
            record.contract_start_date = contract.date_start if contract else False
            record.contract_end_date = contract.date_end if contract else False
            record.employee_identification_number = employee.identification_id if employee else False
            record.contract_type = contract.contract_type_id.name if contract and contract.contract_type_id else False
            record.job_position = contract.job_id.name if contract and contract.job_id else False

    @api.depends("contract_start_date", "settlement_cutoff_date", "absences_days")
    def _compute_days(self):
        for record in self:
            if record.contract_start_date and record.settlement_cutoff_date:
                total_days = (record.settlement_cutoff_date - record.contract_start_date).days + 1

                # Aplica tope de 360 días
                days_in_contract = min(total_days, 360)

                # Días liquidados descontando ausencias
                days_liquidated = max(0, days_in_contract - record.absences_days)

                # Asignar resultados
                record.days_in_contract = days_in_contract
                record.days_liquidated = days_liquidated
            else:
                record.days_in_contract = 0
                record.days_liquidated = 0
                
    def action_generate_settlement_lines(self):
        """Genera las líneas según los conceptos predefinidos"""
        lines = []
        concepts = ['vacaciones', 'prima', 'cesantias', 'intereses_cesantias']

        for concept in concepts:
            vals_line = self._get_line_vals(concept)
            if vals_line:
                lines.append((0, 0, vals_line))

        self.line_ids = [(5, 0, 0)] + lines

    def _get_line_vals(self, concept):
        """Devuelve el diccionario de valores por concepto"""
        ipdb.set_trace()
        contract = self.employee_id.contract_id
        wage = contract.wage
        days_period = (self.settlement_cutoff_date - contract.date_start).days + 1

        # Cálculos base (ejemplo)
        if concept == 'vacaciones':
            value = wage * days_period / 720
        elif concept == 'prima':
            value = wage * days_period / 360
        elif concept == 'cesantias':
            value = wage * days_period / 360
        elif concept == 'intereses_cesantias':
            ces = wage * days_period / 360
            value = ces * 0.12 * days_period / 360
        else:
            value = 0

        return {
            'concept': concept.replace('_', ' ').title(),
            'start_date': contract.date_start,
            'end_date': self.settlement_cutoff_date,
            'days_period': days_period,
            'absences': 0,
            'days_settlement': days_period,
            'average_wage': wage,
            'value_wage': value,
            'advances': 0,
            'net_value': value,
        }