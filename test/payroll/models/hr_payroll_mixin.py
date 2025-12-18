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
        """
        Obtiene los empleados con contrato activo dentro de un rango de fechas.
        
        El método busca empleados con contrato en estado `open` y valida que
        el contrato tenga vigencia dentro del período definido por `date_start`
        y `date_end`. Los empleados que no tengan un contrato válido en el rango
        son omitidos y registrados en el log como advertencia.
        
        Args:
            date_start (date): Fecha de inicio del período a buscar.
            date_end (date): Fecha de fin del período a buscar.
        
        raise:
            UserError: Se activa cuando no hay empleados con contrato 
            activo en el rango de fechas
        
        return:
            retorna el diccionario con los empleados y contratos dentro de las fechas
        
        """

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
        """
        Obtiene los eventos de un empleado dentro de un rango de fechas.

        Este método busca los eventos asociados a un empleado que ocurrieron
        dentro del rango de fechas proporcionado, incluyendo los eventos cuya
        fecha de inicio es antes de la fecha final y cuya fecha de fin es después
        de la fecha inicial del período.

        Args:
            employee_id (int): ID del empleado para el cual se buscan los eventos.
            date_start (date): Fecha de inicio del rango de fechas.
            date_end (date): Fecha de fin del rango de fechas.

        Returns:
            recordset: Un conjunto de registros (`hr.payroll.events`) con los eventos
            que coinciden con el rango de fechas especificado para el empleado.
        """
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
        """
        Obtiene los parámetros de configuración vigentes para un año específico.

        El año se determina a partir de la fecha proporcionada. Con base en ese año,
        el método busca el registro correspondiente en `hr.parameters` y retorna
        los valores configurados que se utilizan en los cálculos de nómina,
        aportes y conceptos relacionados.

        Args:
            date (date | str): Fecha a partir de la cual se determina el año
            de los parámetros a utilizar.

        Raises:
            UserError: Si no existe configuración de parámetros para el año calculado.

        Returns:
            dict: Diccionario con los parámetros vigentes del año, que incluye:
                - minimum_wage
                - transport_allowance
                - uvt_value
                - company_eps_pct
                - employee_eps_pct
                - employee_sena_pct
                - company_pension_pct
                - employee_pension_pct
                - compensation_fund_pct
                - sena_pct
                - icbf_pct
        """
        year = date.year if hasattr(date, "year") else fields.Date.from_string(date).year

        # === Busca Los Parametros Segun El Año Seleccionado En El Periodo De Nomina ===
        record = self.env['hr.parameters'].search([("year", "=", year)], limit=1)
        
        # === Verifica Que Los Parametros Esten Definidos ===
        if not record:
            raise UserError(f"El parámetro del año {year} no está definido en parametros contabilidad")

        # === Retorna Los Valores Vigentes Para El Año ===
        return {
            "minimum_wage": record.minimum_wage,
            "transport_allowance": record.transport_allowance,
            "uvt_value": record.uvt_value,
            "company_eps_pct": record.company_eps_pct,
            "employee_eps_pct": record.employee_eps_pct,
            "employee_sena_pct": record.employee_sena_pct,
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
        """
        Calcula los días a trabajar y los días efectivamente trabajados dentro de un período.

        Este método analiza los eventos asociados a un período y ajusta los días
        trabajados en función de incapacidades, ausencias y otros conceptos que
        afectan el cómputo de días. Los resultados se almacenan directamente en el
        diccionario `totals`.

        Si no existen eventos que afecten el período, se asume que el empleado
        trabajó la totalidad de los días del período.

        Args:
            events (recordset): Conjunto de eventos asociados al período.
            totals (dict): Diccionario de acumuladores que será modificado en sitio.
            date_start (date): Fecha de inicio del período de cálculo.
            date_end (date): Fecha de fin del período de cálculo.
            dates (dict): Diccionario con las fechas seccionadas del período.

        Returns:
            dict: El mismo diccionario `totals` con los siguientes valores actualizados:
                - days_to_work
                - days_worked
                - incapacity_days
                - incapacity_days_unique
                - otros acumuladores derivados de eventos
        """
        
        # === Filtra Todos Los Eventos Que Pertenezcan A Incapacidades ===
        allowed_types = ['sick_leave', 'paid_leave', 'unpaid_leave','suspension', 'parental_leave', 'arl_leave']
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
        """
        Calcula el auxilio de transporte de forma proporcional a los días liquidados.

        Aplica únicamente si el salario no supera dos salarios mínimos y el contrato
        no corresponde a aprendices ni prácticas. Si no cumple las condiciones,
        retorna 0.0.

        Args:
            wage (float): Salario mensual del trabajador.
            days_worked (float): Días liquidados en el período.
            min_wage (float): Salario mínimo vigente.
            allowance (float): Auxilio de transporte mensual vigente.
            contract (recordset): Contrato del trabajador.

        Returns:
            float: Valor del auxilio de transporte calculado.
        """        
        if not contract.sena_apprentice and not contract.apprentice_type == 'academic' or not contract.intern:  
            if wage <= (2 * min_wage):
                return (allowance / 30.0) * days_worked
        return 0.0
    # ========================
    
    
    # ========================
    # Recibe los parametros anuales y retorna los totales de las contribuciones 
    # ========================
    @api.model
    def _compute_contributions(self, totals, company_eps_pct, employee_eps_pct, employee_sena_pct,
                               company_pension_pct, employee_pension_pct, minimum_wage, contract):
        """
        Calcula los aportes a seguridad social según el contrato y las condiciones
        generales del período de nómina.

        Aplica o excluye contribuciones dependiendo del tipo de contrato,
        la base parafiscal, la existencia de licencias y el nivel salarial.
        El resultado se acumula directamente en el diccionario de totales.

        Args:
            totals (dict): Diccionario con los valores acumulados de nómina.
            company_eps_pct (float): Porcentaje EPS empresa.
            employee_eps_pct (float): Porcentaje EPS trabajador.
            employee_sena_pct (float): Porcentaje EPS para aprendices.
            company_pension_pct (float): Porcentaje pensión empresa.
            employee_pension_pct (float): Porcentaje pensión trabajador.
            minimum_wage (float): Salario mínimo vigente.
            contract (recordset): Contrato del trabajador.

        Returns:
            dict: Diccionario `totals` actualizado con los aportes calculados.
        """
        
        arl_fee_pct= self._assign_arl(contract.arl_fee)
        if totals['parental_leave'] < 1:
            totals['arl_contribution'] = totals['parafiscal_base'] * arl_fee_pct / 100.0
        if contract.intern:
            return totals
        if totals['parental_leave'] > 0:
            totals['parafiscal_base'] += totals['parental_leave'] 
        if not contract.sena_apprentice and not contract.apprentice_type == 'academic':
            totals['pension_contribution'] = totals['parafiscal_base'] * employee_pension_pct / 100.0
            totals['company_pension_contribution'] = (totals['parafiscal_base'] * company_pension_pct / 100.0)
            totals['health_contribution'] = totals['parafiscal_base'] * employee_eps_pct / 100.0
        if totals['gross'] >= minimum_wage*10:
            totals['company_health_contribution'] = totals['parafiscal_base'] * company_eps_pct / 100.0
        if contract.sena_apprentice and contract.apprentice_type == 'academic':
            totals['health_contribution'] = totals['parafiscal_base'] * employee_sena_pct / 100.0
        return totals
    # ========================
    
    
    # ========================
    # Recibe Los Parametros Anuales Y Asigna Devuelve Los Aportes Parafiscales Correspondientes 
    # ========================
    @api.model
    def _compute_parafiscal_contributions(self, totals, compensation_fund_pct, sena_pct,
                               icbf_pct, minimum_wage, contract):
        """
        Calcula los aportes parafiscales según las condiciones generales del contrato
        y del período de nómina.

        Aplica o excluye aportes parafiscales dependiendo de la existencia de licencias,
        el nivel salarial y la configuración del contrato.

        Args:
            totals (dict): Diccionario con los valores acumulados de nómina.
            compensation_fund_pct (float): Porcentaje de caja de compensación.
            sena_pct (float): Porcentaje de aporte al SENA.
            icbf_pct (float): Porcentaje de aporte al ICBF.
            minimum_wage (float): Salario mínimo vigente.
            contract (recordset): Contrato del trabajador.

        Returns:
            dict: Diccionario `totals` actualizado con los aportes parafiscales aplicables.
        """
        if totals['parental_leave'] > 0:
            return totals
        if totals['gross'] >= minimum_wage*10:
            totals['sena'] = totals['parafiscal_base'] * sena_pct / 100.0
            totals['icbf'] = totals['parafiscal_base'] * icbf_pct / 100.0
        if contract.compensation_check:
            totals['compensation_fund'] = (totals['parafiscal_base'] * compensation_fund_pct / 100.0)


        return totals
    # ========================
    
    
    # ========================
    # Recibe los parametros anuales y retorna los totales de las prestaciones sociales
    # ========================
    @api.model
    def _compute_benefits(self, totals,  wage_per_day, days_to_work, absences, contract):
        """
        Calcula las prestaciones sociales del trabajador según las condiciones
        del contrato y los días efectivamente trabajados.

        Aplica las prestaciones únicamente cuando el tipo de contrato lo permite
        y ajusta el salario promedio según ausencias y conceptos variables.

        Args:
            totals (dict): Diccionario con los valores acumulados de nómina.
            wage_per_day (float): Salario diario del trabajador.
            days_to_work (float): Días base del período de nómina.
            absences (float): Días no trabajados.
            contract (recordset): Contrato del trabajador.

        Returns:
            dict: Diccionario `totals` actualizado con las prestaciones calculadas.
        """
        
        if contract.intern:
            return totals

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
        """
        Calcula los días del periodo que deben tenerse en cuenta para la liquidación.

        Determina los días base del periodo según el concepto a liquidar.
        Para prima aplica una lógica especial de fechas (desde el 1 de julio),
        mientras que para los demás conceptos toma el periodo completo del contrato.
        Los valores calculados se almacenan directamente en el diccionario de totales.

        Args:
            concept (str): Concepto de liquidación.
                Ejemplo: 'prima', 'cesantias', 'intereses_cesantias', 'vacaciones'.
            events (recordset): Eventos del empleado dentro del periodo evaluado.
            start_date (date): Fecha inicial del periodo a liquidar.
            end_date (date): Fecha final del periodo a liquidar.
            totals (dict): Diccionario acumulador donde se guardan los resultados
                del cálculo.

        Returns:
            dict: Diccionario `totals` actualizado con la clave `period_days`
            y, cuando no existen eventos, `settlement_days`.
        """
        # === Trae El Total De Dias Laborales ===
        if concept == 'prima':
            start_date_prima = date(2025,7,1)
            if start_date_prima > end_date:
                totals['period_days'] = self._calculate_total_settlement_days(start_date, end_date)
            elif start_date_prima >= start_date:
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
    # Computa Los Dias A Liquidar
    # ========================
    def _compute_service_bonus_days(self, events, start_date, end_date, totals):
        
        # === Trae El Total De Dias Laborales ===
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
        """
        Calcula el salario base y el salario promedio para la liquidación.

        A partir del salario del contrato y los días del periodo, determina el
        salario base a liquidar y ajusta el promedio mensual según el concepto.
        En vacaciones, el auxilio de transporte no se incluye en el promedio.
        También descuenta las ausencias no remuneradas.

        Args:
            totals (dict): Diccionario acumulador donde se guardan los resultados.
            contract_wage (float): Salario mensual del contrato.
            period_days (int): Total de días del periodo a liquidar.
            commissions (float): Valor total de comisiones del periodo.
            transport_value (float): Valor del auxilio de transporte del periodo.
            absences (int): Días de ausencia no remunerados.
            concept (str): Concepto de liquidación
                ('prima', 'cesantias', 'intereses_cesantias', 'vacaciones').

        Returns:
            dict: Diccionario `totals` actualizado con el salario promedio calculado.
        """
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
        """
        Calcula el valor a pagar del concepto de liquidación.

        Determina el monto del concepto según su tipo y los días a liquidar,
        usando el salario promedio previamente calculado. Cada concepto
        aplica reglas distintas (vacaciones, prima, cesantías e intereses).

        Args:
            concept (str): Concepto de liquidación
                ('vacaciones', 'prima', 'cesantias', 'intereses_cesantias').
            totals (dict): Diccionario con los valores base del cálculo
                (salario promedio, días a liquidar, etc.).

        Returns:
            dict: Diccionario `totals` actualizado con el valor liquidado
            del concepto en la clave `value_wage`.
        """
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
        """ Asigna el valor del arl """
    
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
        """
        Calcula la intersección (overlap) entre dos rangos de fechas.
        
        Este método recibe dos rangos de fechas independientes y calcula el
        tramo común entre ambos. El resultado se retorna en un diccionario que
        incluye los rangos originales y las fechas resultantes de la intersección.
        
        No valida la existencia de una intersección real; únicamente calcula
        los límites teóricos del solapamiento.
        
        Args:
            event_date_start (date): Fecha de inicio del primer rango.
            event_date_end (date): Fecha de fin del primer rango.
            date_start (date): Fecha de inicio del segundo rango.
            date_end (date): Fecha de fin del segundo rango.

        Returns:
            dict: Diccionario con las siguientes claves:
                - d1: Fecha de inicio del segundo rango.
                - d2: Fecha de fin del segundo rango.
                - e1: Fecha de inicio del primer rango.
                - e2: Fecha de fin del primer rango.
                - o1: Fecha de inicio del rango de intersección.
                - o2: Fecha de fin del rango de intersección.
        """
        
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
        """
        Calcula la cantidad de días trabajados ajustando reglas especiales de calendario.

        Este método calcula los días entre dos fechas ya seccionadas (`o1` y `o2`)
        y aplica ajustes específicos según el mes del período, como correcciones
        para febrero y meses con 31 días.

        No valida la coherencia de las fechas; asume que el diccionario `dates`
        contiene valores correctos y previamente calculados.

        Args:
            dates (dict): Diccionario con fechas seccionadas que incluye, al menos:
                - d1: Fecha de inicio del período.
                - d2: Fecha de fin del período.
                - o1: Fecha de inicio del rango efectivo.
                - o2: Fecha de fin del rango efectivo.

        Returns:
            int: Número de días trabajados ajustado según las reglas del calendario.
        """
        
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
        """
        Ajusta el total de días trabajados descontando incapacidades y aplicando
        reglas especiales según la cantidad de días del mes.

        A diferencia de `_adjust_days_worked_unique`, este método considera el
        número total de días de incapacidad acumulados y realiza ajustes
        adicionales dependiendo del mes (febrero o meses con día 31), así como
        reglas excepcionales cuando las incapacidades son muy bajas o iguales
        o superiores a los días laborables.

        Este método asume que los rangos de fechas ya fueron seccionados y que
        `days_to_work` representa el total base de días del período.

        Args:
            split_dates (list[dict]): Lista de rangos de fechas seccionados.
                Se utiliza únicamente el primer elemento para determinar el mes
                del período.
            incapacity_days (int): Total de días de incapacidad acumulados.
            days_to_work (int): Total base de días laborables del período.

        Returns:
            int: Total de días trabajados ajustados según reglas de negocio.
        """
        if (split_dates[0]['d1'].month == 2 and incapacity_days < 25 and days_to_work > 25):
            days_worked = days_to_work - incapacity_days +2
            if incapacity_days >= days_to_work:
                days_worked = days_to_work - incapacity_days
            elif incapacity_days <= 5:
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
        """
        Calcula el total de días acumulados a partir de múltiples rangos de fechas.
    
        Este método recorre una lista de rangos de fechas previamente seccionados
        y calcula los días efectivos de cada rango, aplicando ajustes especiales
        según el mes (por ejemplo, febrero y meses con 31 días). El resultado es
        la suma total de días calculados.
    
        No valida solapamientos entre rangos ni la coherencia de las fechas;
        asume que los rangos proporcionados son correctos.
    
        Args:
            split_dates (list[dict]): Lista de diccionarios de fechas seccionadas.
            Cada diccionario debe contener, al menos:
                - d1: Fecha de inicio del período.
                - d2: Fecha de fin del período.
                - o1: Fecha de inicio del rango efectivo.
                - o2: Fecha de fin del rango efectivo.
            
        Returns:
            int: Total de días calculados a partir de todos los rangos proporcionados.
        """
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
        """
        Computa los días no trabajados correspondientes a un único evento
        de incapacidad y acumula el resultado en el diccionario `totals`.

        Este método aplica las mismas reglas de ajuste por cantidad de días
        del mes (febrero y meses con día 31) utilizadas en los cálculos
        globales, pero limitadas a un solo rango de fechas.

        A diferencia de `_compute_all_unpaid_days`, este método:
        - Opera sobre un único evento seccionado
        - Actualiza el acumulado `incapacity_days_unique`
        - Retorna el valor acumulado, no solo el del evento actual

        Args:
            split (dict): Diccionario con el rango de fechas seccionado del evento.
                Debe contener las claves 'o1', 'o2', 'd1' y 'd2'.
            totals (dict): Diccionario acumulador de totales del cálculo de nómina.

        Returns:
            int: Total acumulado de días de incapacidad únicos.
        """
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