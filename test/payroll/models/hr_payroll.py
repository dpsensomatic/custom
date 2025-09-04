
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
            "gross": 0.0,
            "deductions": 0.0,
            "comissions": 0.0,
            "sick": 0.0,
            "arl": 0.0,
            "extra_hours": 0.0,
            "night_surcharge": 0.0,
            "other": 0.0,
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

        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")
        
        employees = self.env['hr.employee'].search([('contract_id', '!=', False)])
        if not employees:
            _logger.info("No hay empleados con contrato.")
            self.line_ids = [(5, 0, 0)]
            return
        
        # if any(emp.contract_id.state == 'draft' for emp in employees):
        #     _logger.info("Hay empleados con contratos en Borrador")
        #     self.line_ids = [(5, 0, 0)]
        #     return
        
        # quedarte solo con los que están en open
        employees = employees.filtered(lambda e: e.contract_id.state == 'open')

        employee_ids = employees.ids

        # 2) Prefetch: traer todos los eventos del período para todos los empleados
        events = self.env['hr.payroll.events'].search([
            ('employee_id', 'in', employee_ids),
            ('date', '<=', self.date_end),   # empieza antes o dentro del periodo
            ('date_end', '>=', self.date_start),  # termina dentro o después del periodo
        ])


        # 3) Agrupar eventos por empleado (dict: emp_id -> recordset)
        events_by_emp = {}
        for ev in events:
            events_by_emp.setdefault(ev.employee_id.id, []).append(ev)

        lines = []
        for emp in employees:
            contract = emp.contract_id
            if not contract:
                continue

            # Totales por empleado (inicializar)
            totals = self._empty_totals()
            unpaid_days = 0  # acumula cantidad de días que restan del salario (incapacidades/permiso no remunerado)

            emp_events = events_by_emp.get(emp.id, [])
            for ev in emp_events:
                vals = ev.compute_value(self.date_start, self.date_end) or {}
                # sumar todas las claves retornadas por compute_value
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
            
            params = self.env["hr.parameters"].get_parameters_for_date(self.date_start)
            transportation_allowance = params.get("transport_allowance", 0.0)
            minimun_wage = params.get('minimum_wage',0.0)
            two_minimun_wage = minimun_wage*2   


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



            # construir total devengado agregando wage_earned y lo que venga en totals
            total_gross = wage_earned + totals.get('sick', 0.0) + totals.get('arl', 0.0) \
                          + totals.get('extra_hours', 0.0) + totals.get('night_surcharge', 0.0) \
                          + totals.get('comissions', 0.0) + totals.get('other', 0.0) + allow_value

            total_deductions = totals.get('deductions', 0.0)

            # construir línea
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
                'health_contribution': 0.0,   # <-- puedes calcular después
                'pension_contribution': 0.0,  # <-- ...
                'other_deductions': 0.0,
                'deductions': total_deductions,
                'net': total_gross - total_deductions,
            }
            lines.append((0, 0, vals_line))

            _logger.info("Payroll: emp=%s expected=%s unpaid_days=%s days_worked=%s totals=%s",
                         emp.name, expected, unpaid_days, days_worked, totals)

        # escribir líneas (limpiando las anteriores)
        self.line_ids = [(5, 0, 0)] + lines


    def action_generate_accounting_entries(self):
        """Placeholder: evita error de validación hasta implementar la lógica contable."""
        for record in self:
            # No hace nada por ahora, solo evita el error en la vista.
            pass 