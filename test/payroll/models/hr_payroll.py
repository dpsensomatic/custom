
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb
import logging

_logger = logging.getLogger(__name__)


class HrPayroll(models.Model):
    _name = "hr.payroll"
    _description = "Nómina"

    name = fields.Char(string="Nombre", required=True, default="Nómina")
    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin", required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Cerrada'),
    ], string="Estado", default="draft")

    line_ids = fields.One2many("hr.payroll.line", "payroll_id", string="Líneas de nómina")

    # -------------------------
    # Helpers pequeños
    # -------------------------
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return { 
                # Employee info
                'employee_id':0.0,
                'contract_id': 0.0,
                'base_wage': 0.0,
                'wage_earned': 0.0,
                'days_worked': 0.0,
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'transportation_allowance': 0.0,
                'night_surcharge': 0.0,
                'other_earnings':0.0,
                'gross': 0.0,
                'health_contribution': 0.0,
                'pension_contribution': 0.0, 
                'other_deductions': 0.0,
                'deductions': 0.0,
                'net':0.0,
                
                # Employer contributions
                'arl_contribution': 0.0,
                'total_deductions': 0.0,
                'company_health_contribution': 0.0, 
                'company_pension_contribution': 0.0,
                'total_net': 0.0,
        }
        
        
    def _expected_workdays(self, contract, date_start, date_end):
        """Normaliza todos los meses a 30 días (base contable de 360 días/año)."""
        if not date_start or not date_end:
            return 30
        return 30
    

    # -------------------------
    # Acción principal
    # -------------------------
    def action_generate_lines(self):
        """Genera automáticamente una línea de nómina consolidada por empleado."""
        self.ensure_one()

        # ==========================
        # Validaciones iniciales
        # ==========================
        
        # Valida fechas
        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")
        
        # Trae empleados con contrato activo
        employees = self.env['hr.employee'].search([('contract_id', '!=', False)])
        if not employees:
            _logger.info("No hay empleados con contrato.")
            self.line_ids = [(5, 0, 0)]
            return
        
        # Valida que no haya contratos en estado 'draft' 
        # if any(emp.contract_id.state == 'draft' for emp in employees):
        #     _logger.info("Hay empleados con contratos en Borrador")
        #     self.line_ids = [(5, 0, 0)]
        #     return
        
        
        # Filtra solo contratos con estado 'open'
        employees = employees.filtered(lambda e: e.contract_id.state == 'open')
        # Guardar IDs de empleados
        employee_ids = employees.ids
        
        # ==========================
        # ==========================
        
        
        # ==========================
        # Prefetch: traer todos los eventos del período para todos los empleados
        # ==========================
        
        # Trae todos los eventos de nómina en el rango de fechas para los empleados seleccionados
        events = self.env['hr.payroll.events'].search([
            ('employee_id', 'in', employee_ids), 
            ('date', '<=', self.date_end),
            ('date_end', '>=', self.date_start), 
        ])

        # ==========================
        # ==========================


        # ==========================
        # Agrupar eventos por empleado (dict: emp_id -> recordset)
        # ==========================
        
        # Crea un diccionario para agrupar eventos por empleado segun su ID
        events_by_emp = {}
        for ev in events:
            events_by_emp.setdefault(ev.employee_id.id, []).append(ev)
            
        # Crea un diccionario para posteriormente agregar las líneas de Nomina
        lines = []
        
        # Hace un ciclo por cada empleado
        for emp in employees:
            contract = emp.contract_id
            if not contract:
                continue

        # ==========================
        # ==========================
        
        
            # ==========================
            # Inicializar totales y variables locales
            # ==========================
            totals = self._empty_totals()
            unpaid_days = 0  # acumula cantidad de días que restan del salario (incapacidades/permiso no remunerado)

            # ==========================
            # Procesar eventos del empleado
            # ==========================
            emp_events = events_by_emp.get(emp.id, [])
            for ev in emp_events:
                vals = ev._compute_value(self.date_start, self.date_end) or {}
                # sumar todas las claves retornadas por _compute_value
                for k, v in vals.items():
                    # solo sumar numéricos
                    try:
                        totals[k] = totals.get(k, 0.0) + float(v or 0.0)
                    except Exception:
                        pass

                # para el descuento por días usamos 'quantity' en ciertos tipos
                if ev.type in ['sick_leave', 'arl_leave', 'unpaid_leave']:
                    event_start = ev.date
                    event_end = ev.date + timedelta(days=(ev.quantity or 0) - 1)

                    # calcular la intersección entre evento y periodo de la nómina
                    overlap_start = max(event_start, self.date_start)
                    overlap_end = min(event_end, self.date_end)
                    if overlap_start <= overlap_end:
                        days_in_period = (overlap_end - overlap_start).days + 1
                        unpaid_days += days_in_period
            
            # ==========================
            # Traer variables de otros modelos (parámetros laborales)
            # ==========================
            params = self.env["hr.parameters"].get_parameters_for_date(self.date_start)
            transportation_allowance = params.get("transport_allowance", 0.0)
            minimun_wage = params.get('minimum_wage',0.0)
            two_minimun_wage = minimun_wage*2   

            # ==========================
            # Inicializar variables para cálculos
            # ==========================
            expected = self._expected_workdays(contract, self.date_start, self.date_end)
            
            # asegurarnos de que unpaid_days nunca deje pasar más de 30 días
            days_worked = max(0, expected - unpaid_days)
            
            # si el mes tiene 31 y todo fue incapacidad → unpaid_days=31
            # corregimos a un tope de expected (30)
            if unpaid_days > expected:
                unpaid_days = expected
                days_worked = 0
            wage_earned = (contract.wage * (days_worked / expected)) if expected else 0.0
            
            # Auxilio de transporte: control seguro si no existe el campo booleano
            allow_value = 0.0
            # Si usas un boolean en contrato para indicar si recibe auxilio:
            if contract.wage <= two_minimun_wage:
                allow_value = (transportation_allowance/30)*days_worked

            # ==========================
            # Cálculo de devengados y deducciones
            # ==========================
            total_gross = wage_earned + totals.get('sick', 0.0) + totals.get('arl', 0.0) \
                          + totals.get('extra_hours', 0.0) + totals.get('night_surcharge', 0.0) \
                          + totals.get('comissions', 0.0) + totals.get('other', 0.0) + allow_value
                          
            parameters = self.env['hr.parameters'].get_parameters_for_date(self.date_start)
            company_pension_percentage = parameters['company_pension_percentage']
            company_health_percentage = parameters['company_eps_percentage']
            arl_fee = parameters['arl_fee']
            employee_eps_percentage = parameters['employee_eps_percentage']
            employee_pension_percentage = parameters['employee_pension_percentage']

            arl_fee_value = 0.0
            company_health_contribution = 0.0
            company_pension_contribution = 0.0
            health_contributions = 0.0
            pension_contributions = 0.0
            total_deductions = 0.0
            total_deductions_employee = 0.0
            base_contribution = total_gross - allow_value 
            if base_contribution > 0:
                health_contributions = base_contribution * (employee_eps_percentage / 100)
                pension_contributions = base_contribution * (employee_pension_percentage / 100)
                if total_gross >minimun_wage * 10:
                    company_health_contribution = base_contribution * (company_health_percentage / 100)
                else: 
                    company_health_contribution = 0.0
                company_pension_contribution = base_contribution  * (company_pension_percentage / 100)
                arl_fee_value = (base_contribution * (arl_fee / 100))
                total_deductions_employee = health_contributions + pension_contributions
                total_deductions = total_deductions_employee + arl_fee_value +company_health_contribution+ company_pension_contribution

            # ==========================
            # Construcción de la línea de nómina
            # ==========================
            vals_line = {
                'employee_id': emp.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,
                'wage_earned': wage_earned,
                'days_worked': days_worked,
                'sick_leave': totals.get('sick', 0.0)+ totals.get('arl', 0.0),
                'overtime_hours': totals.get('extra_hours', 0.0),
                'transportation_allowance': allow_value,
                'night_surcharge': totals.get('night_surcharge', 0.0),
                'other_earnings': totals.get('comissions', 0.0) + totals.get('other', 0.0),
                'gross': total_gross,
                'health_contribution': health_contributions,   # <-- puedes calcular después
                'pension_contribution': pension_contributions, 
                'company_health_contribution': company_health_contribution,   # <-- puedes calcular después
                'company_pension_contribution': company_pension_contribution,# <-- ...
                'arl_contribution': arl_fee_value,
                'other_deductions': 0.0,
                'deductions': total_deductions_employee,
                'total_deductions': total_deductions,
                'net': total_gross - total_deductions,
                'total_net': total_gross + total_deductions,
            }
            lines.append((0, 0, vals_line))

            # ==========================
            # Logging de resultados por empleado
            # ==========================
            _logger.info("Payroll: emp=%s expected=%s unpaid_days=%s days_worked=%s totals=%s",
                         emp.name, expected, unpaid_days, days_worked, totals)

        # ==========================
        # Escritura de líneas (limpiando las anteriores)
        # ==========================
        self.line_ids = [(5, 0, 0)] + lines

    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass 