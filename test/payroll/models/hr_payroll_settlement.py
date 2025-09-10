
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
    wage_accrued = fields.Float(string="Salario devengado", compute="_compute_wage")
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

    @api.depends("contract_start_date", "settlement_cutoff_date")
    def _compute_days(self):
        for record in self:
            if record.contract_start_date and record.settlement_cutoff_date:
                record.days_in_contract = (record.settlement_cutoff_date - record.contract_start_date).days + 1
                record.days_liquidated = record.days_in_contract - record.absences_days
            else:
                record.days_in_contract = 0
                record.days_liquidated = 0

    @api.depends("contract_id", "days_liquidated")
    def _compute_wage(self):
        for record in self:
            if record.contract_id and record.days_liquidated:
                daily_wage = record.contract_id.wage / 30
                record.wage_accrued = daily_wage * record.days_liquidated
            else:
                record.wage_accrued = 0

    def action_generate_lines_settlement(self):
        self.ensure_one()
        if not self.contract_id or not self.settlement_cutoff_date:
            raise UserError("Debe definir contrato y fecha de corte.")

        benefits = self._compute_settlement_benefits(self.contract_id, self.settlement_cutoff_date)

        # limpiar anteriores
        self.line_ids = [(5, 0, 0)]  

        # crear líneas
        self.line_ids = [
            (0, 0, {"name": "Prima de servicios", "amount": benefits["service_bonus"]}),
            (0, 0, {"name": "Cesantías", "amount": benefits["severance"]}),
            (0, 0, {"name": "Intereses sobre cesantías", "amount": benefits["interest_on_severance"]}),
            (0, 0, {"name": "Vacaciones", "amount": benefits["vacations"]}),
        ]

        self.state = "done"
    
    def _compute_settlement_benefits(self, contract, cutoff_date):
        self.ensure_one()
        if not contract.date_start:
            return {}
    
        # días trabajados en el contrato hasta la fecha de corte
        days_worked = (cutoff_date - contract.date_start).days + 1
        days_worked = min(days_worked, 360)  # máx 1 año
    
        wage = contract.wage  # salario mensual normal
    
        # Cálculos legales aproximados
        service_bonus = (wage * days_worked) / 360
        severance = (wage * days_worked) / 360
        interest_on_severance = severance * 0.12 * (days_worked / 360)
        vacations = (wage * days_worked) / 720  # 15 días por año → 1/24 del salario
    
        return {
            "service_bonus": service_bonus,
            "severance": severance,
            "interest_on_severance": interest_on_severance,
            "vacations": vacations,
        }