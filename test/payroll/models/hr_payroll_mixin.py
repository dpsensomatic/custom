from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import date
import logging
import ipdb
_logger = logging.getLogger(__name__)


# ========================
# Modelo Base Para Calculos/Funciones
# ========================
class HrPayrollMixin(models.AbstractModel):
    
    # === Descripcion Del Modelo ===
    _name = "hr.payroll.mixin"
    _description = "Funciones comunes para cálculos de nómina"
    
# ========================
    
# ========================
# Buscar Y Traer Informacion
# ========================

    # ========================
    # Traer Trabajadores y sus contratos
    # ========================
    @api.model
    def _get_employees_with_contracts(self, date_start, date_end):

        employees = self.env['hr.employee'].search([('contract_id.state', '=', 'open')])
        if not employees:
            raise UserError(f"No hay empleados con contrato activo en el rango de fechas {date_start}- {date_end}")
    
        result = {}
        skipped = []
        for emp in employees:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', emp.id),
                ('date_start', '<=', date_end),
                '|',
                ('date_end', '>=', date_start),
                ('date_end', '=', False)
            ], limit=1)
    
            # if not contract:
            #     raise UserError(f"El empleado {emp.name} no tiene contrato activo en el rango {date_start} - {date_end}")
            if contract:
                result[emp] = contract
            else:
                # En modo pruebas: solo lo omite, no interrumpe
                skipped.append(emp.name)

            # Log informativo (no interrumpe la ejecución)
            if skipped:
                _logger.warning(f"Empleados sin contrato en el rango {date_start} - {date_end}: {', '.join(skipped)}")
    
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
            "company_eps_pct": record.company_eps_pct,
            "employee_eps_pct": record.employee_eps_pct,
            "company_pension_pct": record.company_pension_pct,
            "employee_pension_pct": record.employee_pension_pct,
            "compensation_fund_pct" : record.compensation_fund_pct,
            "sena_pct": record.sena_pct,
            "icbf_pct": record.icbf_pct,
        }
    # ========================
# ========================
    
# ========================
# Funciones Principales (Estas Funciones Son Llamadas Desde Otros Modelos)
# ========================

  # ========================
  # Payroll   
  # ======================== 
  
    # ========================
    # Computa Los Dias A Pagar Segun Incapacidades 
    # ========================
    @api.model
    def _compute_days_worked(self, events, totals, date_start, date_end, dates):
        
        # === Filtra Todos Los Eventos Que Pertenezcan A Incapacidades ===
        allowed_types = ['sick_leave', 'unpaid_leave', 'arl_leave']
        allowed_events =  events.filtered(lambda e: e.type in allowed_types)
        
        # === Si No Hay Eventos Se Guardan Los Dias Trabajados En 30 ===
        if not allowed_events: 
            totals['days_to_work']= self._adjust_days_worked_unique(dates)
            totals['days_worked'] = totals['days_to_work']
            return totals
        
        # === Se Seccionan Las Fechas Y Se Traen Los Totales De Dias De Incapacidad ===
        split_dates=[]
        for event in allowed_events:
            result = self._split_event_dates(event.date, event.date_end, date_start, date_end)
            if result:
                split_dates.append(result)

        totals['incapacity_days'] = self._compute_all_unpaid_days(split_dates)

        # === Se Ajustan Los Dias Trabajados Segun Los Dias Del Mes === 
        totals['days_to_work'] = self._adjust_days_worked_unique(dates)
        totals['days_worked']= self._adjust_days_worked(split_dates, totals['incapacity_days'],totals['days_to_work'])

        # === Recorre Los Eventos Trayendo Los Valores Segun Incapacidades ===
        for ev, split in zip(events, split_dates):
            
            # === Trae La Incapacidad Por Cada Evento === 
            totals['incapacity_days_unique'] = 0.0
            totals['incapacity_days_unique'] = self._compute_single_unpaid_days(split, totals)
            
            
            # === Llama a la funcion encargada de asignar los valores segun el diccionario ===
            vals = ev._compute_value(totals['incapacity_days_unique']) or {}
            for k, v in vals.items():
                try:
                    totals[k] = totals.get(k, 0.0) + float(v or 0.0)
                except Exception:
                    pass
        
        return totals
    # ========================
    
    
    # ========================
    # Retorna El total A Pagar Para El Trabajador
    # ========================
    def _compute_total_gross(self, totals):
            totals= totals['wage_earned'] + totals['sick_leave'] + totals['overtime_hours'] + totals['commissions'] + totals['other'] + totals['transportation_allowance']
            return totals
    # ========================
    
    
    # ========================
    # Auxilio de transporte
    # ========================
    @api.model
    def _compute_transport_allowance(self, wage, days_worked, min_wage, allowance, contract):
        """Calcula auxilio de transporte según el SMMLV."""
        if not contract.sena_apprentice and not contract.apprentice_type == 'academic':  
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
        if totals['gross'] >= minimum_wage*10 or contract.sena_apprentice:
            totals['company_health_contribution'] = totals['gross'] * company_eps_pct / 100.0
        if not contract.sena_apprentice and not contract.apprentice_type == 'academic':  
            totals['company_pension_contribution'] = (totals['gross'] * company_pension_pct / 100.0)
            totals['pension_contribution'] = totals['gross'] * employee_pension_pct / 100.0
            totals['health_contribution'] = totals['gross'] * employee_eps_pct / 100.0
        totals['arl_contribution'] = totals['gross'] * arl_fee_pct / 100.0
        return totals
    # ========================
    
    
    # ========================
    # Recibe Los Parametros Anuales Y Asigna Devuelve Los Aportes Parafiscales Correspondientes 
    # ========================
    @api.model
    def _compute_parafiscal_contributions(self, totals, compensation_fund_pct, sena_pct,
                               icbf_pct, minimum_wage, contract):
        """Recibe el valor base de las contribuciones y aplica los cálculos."""
        if totals['gross'] >= minimum_wage*10:
            totals['sena'] = totals['gross'] * sena_pct / 100.0
            totals['icbf'] = totals['gross'] * icbf_pct / 100.0
        if contract.compensation_check:
            totals['compensation_fund'] = (totals['gross'] * compensation_fund_pct / 100.0)


        return totals
    # ========================
    
    
    # ========================
    # Recibe los parametros anuales y retorna los totales de las prestaciones sociales
    # ========================
    @api.model
    def _compute_benefits(self, totals,  wage_per_day, days_to_work, absences, contract):
        
        days_worked = days_to_work - absences
        totals['average_wage'] = (wage_per_day*days_worked)+ totals['commissions'] + totals['transportation_allowance']
        
        if not contract.sena_apprentice and not contract.apprentice_type == 'academic':  
            totals['service_bonus'] = totals['average_wage'] * days_worked / 360
            totals['severance'] = totals['average_wage'] * days_worked / 360
            totals['interest_on_severance'] = totals['average_wage'] * 0.12 * (days_worked / 360)
            
            # === Se Ajusta El Salario Promedio Sin Auxilio De Transporte ===
            totals['average_wage'] = (wage_per_day*days_worked)+totals['commissions']
            totals['vacations'] = totals['average_wage'] *0.0417
            totals['total_provisions'] = totals['service_bonus'] + totals['severance'] + totals['interest_on_severance'] + totals['vacations']
        return totals
    # ========================  

  
  # ========================
  # Settlement
  # ========================
    
    # ========================
    # Computa Los Dias A Liquidar
    # ========================
    def _compute_settlement_days(self, concept, events, start_date, end_date, totals):
        
        # === Trae El Total De Dias Laborales ===
        if concept == 'prima':
            start_date_prima = date(2025,7,1)
            if start_date_prima >= start_date:
                totals['period_days'] = self._calculate_total_settlement_days(start_date_prima, end_date)
            else:
                d1 = fields.Date.from_string(start_date)
                p1 = fields.Date.from_string(start_date_prima)
                overlap_start = max(p1, d1)
                totals['period_days'] = self._calculate_total_settlement_days(overlap_start, end_date)
        else:
            totals['period_days'] = self._calculate_total_settlement_days(start_date, end_date)
        
        if not events:
            totals['settlement_days'] = totals['period_days']
            return totals
        
        return totals
    # ========================


    # ========================
    # Calcula El Salario Base Y Salario Promedio
    # ========================
    def _compute_settlement_totals(self, totals, contract_wage, period_days, commissions, transport_value, absences, concept ):
        # === Consigue El total De Meses Totales A Trabajar ===
        total_months = period_days/30
        
        # === Quita El Auxilio De Transporte Del Promedio En Vacaciones ===
        if concept == 'vacations':
            total_base_wage = (contract_wage*total_months)+commissions
        else:
            total_base_wage = (contract_wage*total_months)+commissions + transport_value
            
        # === Arroja El Total Descontando Las Licencias No Remuneradas
        total_absence_base_wage = total_base_wage-((contract_wage/30)*absences)
        
        # === Retorna El Promedio Mensual ===
        totals['average_wage'] = total_absence_base_wage/total_months
        round(totals['average_wage'])
        return totals    
    # ========================
    
    
    # ========================
    # Calcula Los Totales De La Liquidacion
    # ========================
    def _calculate_liquidated_wage(self, concept, totals):
        
        # === Calcula Segun El Concepto ===
        if concept == 'vacaciones':
            totals['value_wage'] = totals['average_wage'] * totals['settlement_days'] / 720
        elif concept == 'prima':
            totals['value_wage'] = totals['average_wage'] * totals['settlement_days'] / 360
        elif concept == 'cesantias':
            totals['value_wage'] = totals['average_wage'] * totals['settlement_days'] / 360
        elif concept == 'intereses_cesantias':
            ces = totals['average_wage'] * totals['settlement_days'] / 360
            totals['value_wage'] = ces * 0.12 * totals['settlement_days'] / 360
        else:
            totals['value_wage'] = 0
            
        return totals
    # ========================
  # ========================

# ========================


# ========================
# Helpers
# ========================
    
    # ========================
    # Ajusta La Tarifa Del ARL
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
    # ========================
    
    
    # ========================
    # Secciona Las Fechas Y Las Guarda En Un Diccionario
    # ========================
    def _split_event_dates(self, event_date_start, event_date_end, date_start, date_end):
        
        # === Reccorre Los Eventos Y Retorna Las Fechas ===
        d1 = fields.Date.from_string(date_start)
        d2 = fields.Date.from_string(date_end)
        e1 = fields.Date.from_string(event_date_start)
        e2 = fields.Date.from_string(event_date_end)
        overlap_start = max(e1, d1)
        overlap_end = min(e2, d2)
        o1 = fields.Date.from_string(overlap_start)
        o2 = fields.Date.from_string(overlap_end)
        return {
        'd1': d1,
        'd2': d2,
        'e1': e1,
        'e2': e2,
        'o1': o1,
        'o2': o2,
        }
    # ========================
    
    
    # ========================
    # Hace El Calculo De Los Dias Liquidados
    # ========================
    def _calculate_total_settlement_days(self, start_date, end_date):
        """Calcula la diferencia en días usando calendario laboral (360 días/año)."""
        if not start_date or not end_date:
            return 0
        
        d1, m1, y1 = start_date.day, start_date.month, start_date.year
        d2, m2, y2 = end_date.day, end_date.month, end_date.year
        # Ajuste según regla 30/360
        if d1 == 31:
            d1 = 30
        if d2 == 31:
            d2 = 30
        return (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1) + 1
    # ========================

        
    
    
    # ========================
    # Adjusta Los Dias  Trabajados Segun La Cantidad De Dias Del Mes
    # ========================    
    def _adjust_days_worked_unique(self, dates):
        
        days_worked_temporal = dates['o2'].day-dates['o1'].day + 1
        if dates['d1'].month == 2 and days_worked_temporal > 25:
            days_worked = days_worked_temporal + 2
        elif dates['d2'].day == 31 and days_worked_temporal > 30:
            days_worked = days_worked_temporal - 1
        else:
            days_worked = days_worked_temporal

        return days_worked
    # ========================
    
    
    # ========================
    # Adjusta Los Dias  Trabajados Segun La Cantidad De Dias Del Mes
    # ========================    
    def _adjust_days_worked(self, split_dates, incapacity_days, days_to_work):
        if (split_dates[0]['d1'].month == 2 and incapacity_days < 25 and days_to_work > 25):
            days_worked = days_to_work - incapacity_days +2
            if incapacity_days >= days_to_work:
                days_worked = days_to_work - incapacity_days
        elif (split_dates[0]['d2'].day == 31 and incapacity_days < 30 and days_to_work > 30): 
            days_worked = days_to_work - incapacity_days - 1
        else:
            days_worked = days_to_work - incapacity_days

        return days_worked
    # ========================
    
    
    # ========================
    # Computa El Total De Los Dias De Incapacidad
    # ========================
    def _compute_all_unpaid_days(self, split_dates):
        totals = 0
        for split in split_dates:
            unpaid_days = split['o2'].day - split['o1'].day + 1
            if split['d1'].month == 2 and unpaid_days > 25:
                unpaid_days = split['o2'].day - split['o1'].day + 3
            if split['d2'].day == 31 and unpaid_days > 30:
                unpaid_days = split['o2'].day - split['o1'].day 
            totals +=  unpaid_days

        return totals
    # ========================
    
    
    # ========================
    # Computa Un Solo Evento Por Cada Ciclo
    # ========================
    def _compute_single_unpaid_days(self, split, totals):
        # === Dias no trabajados ===
            unpaid_days = split['o2'].day - split['o1'].day + 1
            if split['d1'].month == 2 and unpaid_days > 25:
                unpaid_days = split['o2'].day - split['o1'].day + 3
            if split['d2'].day == 31 and unpaid_days > 30:
                unpaid_days = split['o2'].day - split['o1'].day 
            totals['incapacity_days_unique'] = totals.get('incapacity_days_unique', 0) + unpaid_days
            return totals['incapacity_days_unique']
    # ========================
# ========================