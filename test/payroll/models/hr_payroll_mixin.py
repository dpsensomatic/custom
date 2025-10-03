from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb

class HrPayrollMixin(models.AbstractModel):
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"

    # ========================
    # Traer Trabajadores y sus contratos - hr_employee.py, hr_contract.py
    # ========================
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
    # ========================  
    
    # ========================
    # Helper: obtener parámetros - hr_parameters.py
    # ========================
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
    # ========================
    
    # ========================
    # 
    # ========================
    @api.model
    def _get_events(self, employee_id, date_start, date_end):
        """Devuelve todos los eventos de un empleado en el rango de fechas."""
        return self.env['hr.payroll.events'].search([
            ('employee_id', '=', employee_id),
            ('date', '<=', date_end),
            ('date_end', '>=', date_start),
        ])
    # ========================
        
    
    # ========================
    # Computa Los Dias a pagar segun incapacidades 
    # ========================
    @api.model
    def _compute_days_worked(self, events, totals, date_start, date_end):
        
        # === Si no hay eventos se guardan los dias trabajados en 30 ===
        if not events:
            totals['days_worked'] = 30
            return totals
        
        # === Recorre los eventos/novedades para seleccionar como afectara la nomina ===
        totals['unpaid_days'] = self._compute_totals_unpaid_days(events, totals, date_start, date_end)
        
        # === Se ajusta segun la cantidad de dias del mes === 
        d1 = fields.Date.from_string(date_start)
        d2 = fields.Date.from_string(date_end)

        if d1.month == 2 and totals['unpaid_days'] > 15:
            totals['days_worked'] = 28.0 - totals['unpaid_days']
        elif d2.day == 31 and totals['unpaid_days'] > 15:
            totals['days_worked'] = 31.0 - totals['unpaid_days']
        else:
            totals['days_worked'] = 30.0 - totals['unpaid_days']

        # ========================
        # Recorre los eventos trayendo los valores segun incapacidades
        # ========================
        for ev in events:
            totals['unpaid_days'] = 0.0
            totals['unpaid_days'] = self._compute_unpaid_days(ev, totals, date_start, date_end)

            # === Llama a la funcion encargada de asignar los valores segun el diccionario ===
            vals = ev._compute_value(totals['unpaid_days']) or {}
            for k, v in vals.items():
                try:
                    totals[k] = totals.get(k, 0.0) + float(v or 0.0)
                except Exception:
                    pass
        
        return totals

    def _compute_totals_unpaid_days(self, events, totals, date_start, date_end):
        for ev in events:
            d1 = fields.Date.from_string(date_start)
            d2 = fields.Date.from_string(date_end)
            e1 = fields.Date.from_string(ev.date)
            e2 = fields.Date.from_string(ev.date_end)
            # === Filtra por eventos de incapacidad ===
            if ev.type == "sick_leave":

                # === Verifica que traiga las novedades vigentes en el periodo de nomina ===
                if d1.month == e1.month or d2.month == e2.month:
                    overlap_start = max(ev.date, date_start)
                    overlap_end = min(ev.date_end, date_end)
                    o1 = fields.Date.from_string(overlap_start)
                    o2 = fields.Date.from_string(overlap_end)
                    # === Dias no trabajados ===
                    unpaid_days = o2.day - o1.day + 1
                    totals['unpaid_days'] = totals.get('unpaid_days', 0) + unpaid_days

        return totals['unpaid_days']
    
    def _compute_unpaid_days(self, events, totals, date_start, date_end):
        for ev in events:
            d1 = fields.Date.from_string(date_start)
            d2 = fields.Date.from_string(date_end)
            e1 = fields.Date.from_string(ev.date)
            e2 = fields.Date.from_string(ev.date_end)
            # === Filtra por eventos de incapacidad ===
            if ev.type not in ['sick_leave','arl_leave','unpaid_leave']:
                totals['unpaid_days'] = 0
                return 

                # === Verifica que traiga las novedades vigentes en el periodo de nomina ===
            if d1.month == e1.month or d2.month == e2.month:
                overlap_start = max(ev.date, date_start)
                overlap_end = min(ev.date_end, date_end)
                o1 = fields.Date.from_string(overlap_start)
                o2 = fields.Date.from_string(overlap_end)
                
                # === Dias no trabajados ===
                unpaid_days = o2.day - o1.day + 1
                if d1.month == 2 and unpaid_days > 15:
                    unpaid_days = o2.day - o1.day + 3
                if d2.day == 31 and unpaid_days > 15:
                    unpaid_days = o2.day - o1.day 
                
                totals['unpaid_days'] = totals.get('unpaid_days', 0) + unpaid_days
                return totals['unpaid_days']
                
    
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
    
    # ========================
    # Helpers
    # ========================
    
    