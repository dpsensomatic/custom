from odoo import models, api

class HrPayrollMixin(models.AbstractModel):
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"

    # -----------------------------
    # Helper para obtener parámetros
    # -----------------------------
from odoo import models, api, fields, _
from odoo.exceptions import UserError

class HrPayrollMixin(models.AbstractModel):
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"

    # -----------------------------
    # Helper: obtener parámetros
    # -----------------------------
    @api.model
    def _get_parameter(self, code):
        """Busca un parámetro de nómina según su código (en hr.parameters)."""
        param = self.env['hr.parameters'].search([('code', '=', code)], limit=1)
        if not param:
            raise UserError(_("El parámetro %s no está definido en hr.parameters") % code)
        return float(param.value) if hasattr(param, "value") else float(param.amount)

    # -----------------------------
    # Eventos de nómina
    # -----------------------------
    @api.model
    def _get_events(self, employee_id, date_start, date_end):
        """Devuelve todos los eventos de un empleado en el rango de fechas."""
        return self.env['hr.payroll.events'].search([
            ('employee_id', '=', employee_id),
            ('date_start', '<=', date_end),
            ('date_end', '>=', date_start),
        ])
        
    # -----------------------------
    # Auxilio de transporte
    # -----------------------------
    @api.model
    def compute_transport_allowance(self, wage):
        """Calcula auxilio de transporte según el SMMLV."""
        min_wage = self._get_parameter("MIN_WAGE")
        allowance = self._get_parameter("TRANSPORT_ALLOWANCE")
        return allowance if wage <= (2 * min_wage) else 0.0

    @api.model
    def compute_worked_days(self, employee_id, date_start, date_end):
        """Calcula días trabajados en un período descontando ausencias."""
        total_days = (fields.Date.from_string(date_end) - fields.Date.from_string(date_start)).days + 1
        events = self._get_events(employee_id, date_start, date_end)

        absent_days = 0
        for ev in events:
            # Calcula la intersección entre el evento y el rango
            ev_start = max(fields.Date.from_string(ev.date_start), fields.Date.from_string(date_start))
            ev_end = min(fields.Date.from_string(ev.date_end), fields.Date.from_string(date_end))
            delta = (ev_end - ev_start).days + 1
            absent_days += delta if delta > 0 else 0

        return max(0, total_days - absent_days)

    
    @api.model
    def compute_minimum_wage_with_commissions(self, base_wage, commissions):
        """Salario ajustado según SMMLV"""
        min_wage = float(self._get_parameter("MIN_WAGE"))
        total = base_wage + commissions
        return max(total, min_wage)
    
    
    @api.model
    def wage_earned(self, wage, days_worked):
        """Calcula el salario devengado según días trabajados"""
        return (wage / 30) * days_worked
    
    
    @api.model
    def _compute_benefits(self, total_gross, wage_earned, days_worked):
        service_bonus = total_gross * (days_worked / 360)
        severance = total_gross * (days_worked / 360)
        interest_on_severance = severance * 0.12 * (days_worked / 360)
        vacations = wage_earned *0.0417
        return {
            'service_bonus': service_bonus,
            'severance': severance,
            'interest_on_severance': interest_on_severance,
            'vacations': vacations,
        }
    
    
    @api.model
    def compute_total_gross(self, wage, transport_allowance, events):
        """Calcula el total bruto"""
        return wage + transport_allowance + events