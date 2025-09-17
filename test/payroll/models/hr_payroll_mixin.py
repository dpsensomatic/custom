from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb

class HrPayrollMixin(models.AbstractModel):
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"

    # -----------------------------
    # Traer Trabajadores y sus contratos - hr_employee.py, hr_contract.py
    # -----------------------------
    @api.model
    def _get_employees_with_contracts(self, date_start, date_end):
        """
        Devuelve un diccionario con empleados y su contrato activo en el rango de fechas.
        Formato: {employee_record: contract_record}
        """
        employees = self.env['hr.employee'].search([('contract_id.state', '=', 'open')])
        if not employees:
            raise UserError(f"No hay empleados con contrato activo en el rango de fechas {date_start}- {date_end}")
    
        result = {}
        for emp in employees:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', emp.id),
                ('date_start', '<=', date_end),
                '|',
                ('date_end', '>=', date_start),
                ('date_end', '=', False)
            ], limit=1)
    
            if not contract:
                raise UserError(f"El empleado {emp.name} no tiene contrato activo en el rango {date_start} - {date_end}")
    
            result[emp] = contract
    
        return result
    # -----------------------------    
    
    # -----------------------------
    # Helper: obtener parámetros - hr_parameters.py
    # -----------------------------
    @api.model
    def _get_parameter(self, date):
        """Busca un parámetro de nómina según su año en hr.parameters."""
        year = date.year if hasattr(date, "year") else fields.Date.from_string(date).year

        # Buscar el registro correcto en hr.parameters
        record = self.env['hr.parameters'].search([("year", "=", year)], limit=1)
        if not record:
            raise UserError(f"El parámetro del año {year} no está definido en hr.parameters")

        # Convertir arl_fee a porcentaje
        arl_fee_map = {
            'i': 0.522,
            'ii': 1.044,
            'iii': 2.436,
            'iv': 4.350,
            'v': 6.960,
        }
        arl_fee_value = arl_fee_map.get(record.arl_fee, 0.0)

        return {
            "minimum_wage": record.minimum_wage,
            "transport_allowance": record.transport_allowance,
            "uvt_value": record.uvt_value,
            "company_eps_percentage": record.company_eps_percentage,
            "employee_eps_percentage": record.employee_eps_percentage,
            "company_pension_percentage": record.company_pension_percentage,
            "employee_pension_percentage": record.employee_pension_percentage,
            "arl_fee": arl_fee_value,
        }
    # -----------------------------
    @api.model
    def _get_events(self, employee_id, date_start, date_end):
        """Devuelve todos los eventos de un empleado en el rango de fechas."""
        return self.env['hr.payroll.events'].search([
            ('employee_id', '=', employee_id),
            ('date', '<=', date_end),
            ('date_end', '>=', date_start),
        ])
        
    
    @api.model
    def _diff_360(self, start_date, end_date):
        """Calcula la diferencia en días usando calendario laboral (360 días/año)."""
        if not start_date or not end_date:
            return 0

        d1 = fields.Date.from_string(start_date)
        d2 = fields.Date.from_string(end_date)

        d1_day, d1_month, d1_year = d1.day, d1.month, d1.year
        d2_day, d2_month, d2_year = d2.day, d2.month, d2.year

        # Ajuste según regla 30/360
        if d1_day == 31:
            d1_day = 30
        if d2_day == 31 and d1_day == 30:
            d2_day = 30

        return (d2_year - d1_year) * 360 + (d2_month - d1_month) * 30 + (d2_day - d1_day) + 1
    @api.model
    def _expected_workdays(self, date_start, date_end):
        """Devuelve el número de días del período bajo la convención 30/360."""
        return self._diff_360(date_start, date_end)

    @api.model
    def _compute_days_worked(self, events, totals, date_start, date_end):
        unpaid_days = 0
        for ev in events:
            vals = ev._compute_value(date_start, date_end) or {}
            for k, v in vals.items():
                try:
                    totals[k] = totals.get(k, 0.0) + float(v or 0.0)
                except Exception:
                    pass

            if ev.type in ['sick_leave', 'arl_leave', 'unpaid_leave']:
                event_start = fields.Date.from_string(ev.date)
                event_end = event_start + timedelta(days=(ev.quantity or 0) - 1)

                overlap_start = max(event_start, fields.Date.from_string(date_start))
                overlap_end = min(event_end, fields.Date.from_string(date_end))

                if overlap_start <= overlap_end:
                    days_in_period = self._diff_360(overlap_start, overlap_end)
                    unpaid_days += days_in_period

        return unpaid_days    
    
    
    @api.model
    def compute_worked_days(self, employee_id, date_start, date_end):
        """Calcula días trabajados en un período descontando ausencias bajo 30/360."""
        total_days = self._diff_360(date_start, date_end)
        events = self._get_events(employee_id, date_start, date_end)

        absent_days = 0
        for ev in events:
            ev_start = max(fields.Date.from_string(ev.date_start), fields.Date.from_string(date_start))
            ev_end = min(fields.Date.from_string(ev.date_end), fields.Date.from_string(date_end))

            if ev_start <= ev_end:
                absent_days += self._diff_360(ev_start, ev_end)

        return max(0, total_days - absent_days)    

    # -----------------------------
    # Auxilio de transporte
    # -----------------------------
    @api.model
    def _compute_transport_allowance(self, wage, days_worked, min_wage, allowance):
        """Calcula auxilio de transporte según el SMMLV."""
        if wage <= (2 * min_wage):
            return (allowance / 30.0) * days_worked
        return 0.0


    
    @api.model
    def _compute_contributions(self, arl, company_eps_pct, employee_eps_pct,
                               company_pension_pct, employee_pension_pct, minimum_wage, total_gross, allowance):
        """Recibe el valor base de las contribuciones y aplica los cálculos."""
        if total_gross >= minimum_wage*10:
            company_eps = total_gross * company_eps_pct / 100.0
        else:company_eps= 0.0
        employee_eps = total_gross * employee_eps_pct / 100.0
        company_pension = (total_gross * company_pension_pct / 100.0)
        employee_pension = total_gross * employee_pension_pct / 100.0
        arl_contribution = total_gross * arl / 100.0

        return {
            'company_eps': company_eps,
            'employee_eps': employee_eps,
            'company_pension': company_pension,
            'employee_pension': employee_pension,
            'arl_contribution': arl_contribution,
        }
    
    
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
    