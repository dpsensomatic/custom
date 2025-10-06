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
    # Trae Los eventos 
    # ========================
    @api.model
    def _get_events(self, employee_id, date_start, date_end):

        # === Retorna Los Valores De Los Eventos Segun El Periodo De Nomina ===
        return self.env['hr.payroll.events'].search([
            ('employee_id', '=', employee_id),
            ('date', '<=', date_end),
            ('date_end', '>=', date_start),
        ])
    # ========================
    
    
    # ========================
    # Obtener Parámetros - hr_parameters.py
    # ========================
    @api.model
    def _get_parameter(self, date):
        year = date.year if hasattr(date, "year") else fields.Date.from_string(date).year

        # === Busca Los Parametros Segun El Año Seleccionado En El Periodo De Nomina ===
        record = self.env['hr.parameters'].search([("year", "=", year)], limit=1)
        
        # === Verifica Que Los Parametros Esten Definidos ===
        if not record:
            raise UserError(f"El parámetro del año {year} no está definido en hr.parameters")

        # === Retorna Los Valores Vigentes Para El Año ===
        return {
            "minimum_wage": record.minimum_wage,
            "transport_allowance": record.transport_allowance,
            "uvt_value": record.uvt_value,
            "company_eps_percentage": record.company_eps_percentage,
            "employee_eps_percentage": record.employee_eps_percentage,
            "company_pension_percentage": record.company_pension_percentage,
            "employee_pension_percentage": record.employee_pension_percentage,
        }
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

        # === Recorre los eventos trayendo los valores segun incapacidades ===
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

    # === Computa El Total De Los Dias Incapacidad ===
    def _compute_totals_unpaid_days(self, events, totals, date_start, date_end):
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
                totals['unpaid_days'] = totals.get('unpaid_days', 0) + unpaid_days

        return totals['unpaid_days']
    
    # === Computa Los Dias De Incapacidad ===
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

                # === Verifica Que Haya Novedades Vigentes En El Periodo De Nomina ===
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
    # ========================
    
    
    # ========================
    # Auxilio de transporte
    # ========================
    @api.model
    def _compute_transport_allowance(self, wage, days_worked, min_wage, allowance):
        """Calcula auxilio de transporte según el SMMLV."""
        if wage <= (2 * min_wage):
            return (allowance / 30.0) * days_worked
        return 0.0
    # ========================
    
    
    # ========================
    # Recibe los parametros anuales y retorna los totales de las contribuciones 
    # ========================
    @api.model
    def _compute_contributions(self, totals, company_eps_pct, employee_eps_pct,
                               company_pension_pct, employee_pension_pct, minimum_wage, contract):
        """Recibe el valor base de las contribuciones y aplica los cálculos."""
        arl_fee_pct= self._assign_arl(contract.arl_fee)
        if totals['gross'] >= minimum_wage*10:
            totals['company_health_contribution'] = totals['gross'] * company_eps_pct / 100.0
        else:totals['company_health_contribution'] = 0.0
        totals['company_pension_contribution'] = (totals['gross'] * company_pension_pct / 100.0)
        totals['pension_contribution'] = totals['gross'] * employee_pension_pct / 100.0
        totals['health_contribution'] = totals['gross'] * employee_eps_pct / 100.0
        totals['arl_contribution'] = totals['gross'] * arl_fee_pct / 100.0

        return totals
    # ========================
    
    
    # ========================
    # Recibe los parametros anuales y retorna los totales de las prestaciones sociales
    # ========================
    @api.model
    def _compute_benefits(self, totals):
        totals['service_bonus'] = totals['gross'] * (totals['days_worked'] / 360)
        totals['severance'] = totals['gross'] * (totals['days_worked'] / 360)
        totals['interest_on_severance'] = totals['severance'] * 0.12 * (totals['days_worked'] / 360)
        totals['vacations'] = totals['wage_earned'] *0.0417
        totals['total_provisions'] = totals['service_bonus'] + totals['severance'] + totals['interest_on_severance'] + totals['vacations']
        return totals
    # ========================
    
    
    # ========================
    # Helpers
    # ========================
    def _assign_arl(self, contract):
    
        arl_fee_map = {
            'i': 0.522,
            'ii': 1.044,
            'iii': 2.436,
            'iv': 4.350,
            'v': 6.960,
        }
        arl_fee_value = arl_fee_map.get(contract, 0.0)
        return arl_fee_value
    
    def _compute_total_gross(self, totals):
            totals= totals['wage_earned'] + totals['sick_leave'] + totals['overtime_hours'] + totals['night_surcharge'] + totals['other'] + totals['transportation_allowance']
            return totals
    # ========================