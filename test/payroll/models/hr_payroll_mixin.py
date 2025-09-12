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
                raise UserError("El empleado {emp.name} no tiene contrato activo en el rango {date_start} - {date_end}")
    
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
    
    # -----------------------------
    # Días esperados en el período
    # -----------------------------
    @api.model
    def _expected_workdays(self, date_start, date_end):
        """Devuelve el número de días del período bajo la convención 30/360."""
        if not date_start or not date_end:
            return 30
    
        d1 = fields.Date.from_string(date_start)
        d2 = fields.Date.from_string(date_end)
    
        # Normalizar usando regla de 30/360
        start_day = min(d1.day, 30)
        end_day = min(d2.day, 30)
    
        months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
        days = (end_day - start_day) + (months * 30) + 1
    
        return days
    
    # -----------------------------

    # -----------------------------
    # Eventos de nómina
    # -----------------------------
    # -----------------------------
    # Dias trabajados
    # -----------------------------
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
                event_start = ev.date
                event_end = ev.date + timedelta(days=(ev.quantity or 0) - 1)
                overlap_start = max(event_start, date_start)
                overlap_end = min(event_end, date_end)
                if overlap_start <= overlap_end:
                    days_in_period = (overlap_end - overlap_start).days + 1
                    unpaid_days += days_in_period  # ahora sí existe
    
        return unpaid_days
            
    # -----------------------------
        
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
    