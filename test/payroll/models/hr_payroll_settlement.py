
# ==========================
# Modelo: Liquidación de Nómina
# ==========================
from odoo import fields, models, api
from odoo.exceptions import UserError

class HrPayrollSettlement(models.Model):
    _name = 'hr.payroll.settlement'
    _description = 'Liquidación de Nómina'

    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", required=True)
    line_ids = fields.One2many("hr.payroll.settlement.line", "settlement_id", string="Líneas de Liquidación")

    name = fields.Char(string="Nombre de la liquidacion", required=True)
    settlement_creation_date = fields.Date(string="Fecha de creacion de la liquidacion")
    settlement_cutoff_date = fields.Date(string="Fecha de corte de la liquidacion")
    termination_reason = fields.Char(string="Causa de retiro ")
    contract_start_date = fields.Date(string="Fecha inicio contrato", compute='_compute_contract_fields', store=True)
    contract_end_date = fields.Date(string="Fecha fin contrato", compute='_compute_contract_fields', store=True)
    employee_identification_number = fields.Char(string="Numero de identificacion", compute='_compute_contract_fields', store=True)
    contract_type = fields.Char(string="Tipo de contrato", compute='_compute_contract_fields', store=True)
    job_position = fields.Char(string="Cargo", compute='_compute_contract_fields', store=True)
    days_in_contract = fields.Integer(string="Días contrato", compute="_compute_days")
    absences_days = fields.Integer(string="Ausencia", default=0)  
    days_liquidated = fields.Integer(string="Días liquidados", compute="_compute_days")
    wage_accrued = fields.Float(string="Salario devengado")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)

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
        def diff_360(start_date, end_date):
            """Calcula la diferencia en días usando calendario laboral (360 días/año)."""
            if not start_date or not end_date:
                return 0
            d1, m1, y1 = start_date.day, start_date.month, start_date.year
            d2, m2, y2 = end_date.day, end_date.month, end_date.year
            # Ajuste según regla 30/360
            if d1 == 31:
                d1 = 30
            if d2 == 31 and d1 == 30:
                d2 = 30
            return (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1) + 1
        for record in self:
            if record.contract_start_date and record.settlement_cutoff_date:
                # Diferencia en "meses de 30 días"
                total_days = diff_360(record.contract_start_date, record.settlement_cutoff_date)
                # Aplica tope de 360 días
                days_in_contract = min(total_days, 360)
                # Días liquidados descontando ausencias
                days_liquidated = max(0, days_in_contract - record.absences_days)
                record.days_in_contract = days_in_contract
                record.days_liquidated = days_liquidated
            else:
                record.days_in_contract = 0
                record.days_liquidated = 0

    def action_generate_settlement_lines(self):
        days_liquidated = self.days_liquidated
        days_in_contract = self.days_in_contract
        
