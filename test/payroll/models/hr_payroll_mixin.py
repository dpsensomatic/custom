from odoo import models, api

class HrPayrollMixin(models.AbstractModel):
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"

    # -----------------------------
    # Helper para obtener parámetros
    # -----------------------------
    @api.model
    def _get_parameter(self, code):
        """Busca un parámetro de nómina según su código."""
        param = self.env['hr.parameters'].search([('code', '=', code)], limit=1)
        if not param:
            raise ValueError(f"Parámetro {code} no está definido en hr.parameters")
        return param.value  # O param.amount según cómo lo tengas definido
    
    
    @api.model
    def compute_transport_allowance(self, wage):
        """Auxilio de transporte según el SMMLV"""
        min_wage = float(self._get_parameter("MIN_WAGE"))
        allowance = float(self._get_parameter("TRANSPORT_ALLOWANCE"))
        return allowance if wage <= (2 * min_wage) else 0
    
    
    @api.model
    def _expected_worked_days(self, start_date, end_date):
        """Calcula los días esperados entre dos fechas"""
        delta = (end_date - start_date).days + 1
        return max(delta, 0)

    
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
        