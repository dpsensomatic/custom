from odoo import fields, models, api
from datetime import timedelta
import ipdb
import logging

_logger = logging.getLogger(__name__)

class HrPayrollEvents(models.Model):
    _name = 'hr.payroll.events'
    _description = 'Eventos de Nomina'

    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato")
    type = fields.Selection([
        ('commissions', 'Comisiones'),
        ('day_overtime', 'Hora Extra Diurna'),
        ('sunday_overtime', 'Hora Extra Dominical'),
        ('night_overtime', 'Hora Extra Nocturna'),
        ('night_surcharge', 'Hora Recargo Nocturno'),
        ('sick_leave', 'Incapacidades'),
        ('arl_leave', 'Incapacidad ARL'),
        ('unpaid_leave', 'Permiso No Remunerado'),
    ], string='Tipo de Novedad')
    date = fields.Date(string='Fecha de la Novedad')
    date_end = fields.Date(string="Fecha fin", compute="_compute_date_end", store=True)
    quantity = fields.Integer(string='Cantidad de dias de la novedad')
    unit = fields.Selection([
        ('day', 'Día'),
        ('unit', 'Unidad'),
        ('hour', 'Hora')
    ], string='Tipos de Unidad')

    @api.depends("date", "quantity")
    def _compute_date_end(self):
        for record in self:
            if record.date and record.quantity:
                record.date_end = record.date + timedelta(days=record.quantity - 1)
            else:
                record.date_end = record.date

    def compute_value(self, payroll_start=None, payroll_end=None):
        """Devuelve {'gross': X, 'deductions': Y, ...} según el tipo de novedad.
        Si payroll_start y payroll_end están definidos, solo cuenta los días dentro de ese rango.
        """
        self.ensure_one()

        if not self.contract_id:
            return {"gross": 0.0, "deductions": 0.0, 'sick': 0.0,
                    "extra_hours": 0.0, "night_surcharge": 0.0,
                    'other': 0.0, 'arl': 0.0, 'comissions': 0.0}

        mensual_wage = self.contract_id.wage
        params = self.env["hr.parameters"].get_parameters_for_date(self.date)
        minimum_wage = params.get("minimum_wage", 0.0)
        minimum_day_value = minimum_wage/30        
        day_value = mensual_wage / 30
        day_value_percentage = day_value * 0.6667
        hour_value = day_value / 8

        # === Calcular días efectivos ===
        event_start = self.date
        event_end = self.date_end
        effective_days = self.quantity

        if payroll_start and payroll_end:
            overlap_start = max(event_start, payroll_start)
            overlap_end = min(event_end, payroll_end)
            if overlap_start and overlap_end and overlap_start <= overlap_end:
                effective_days = (overlap_end - overlap_start).days + 1
            else:
                effective_days = 0  # No se cruza con la nómina

        # === Diccionario base ===
        result = {"extra_hours": 0.0, "deductions": 0.0, 'sick': 0.0,
                  "arl": 0.0, 'comissions': 0.0, 'night_surcharge': 0.0, 'other': 0.0}

        # === Cálculos ===
        if self.type == "day_overtime":
            result["extra_hours"] = effective_days * hour_value * 1.25
        elif self.type == "night_overtime":
            result["extra_hours"] = effective_days * hour_value * 1.75
        elif self.type == "commissions":
            result["comissions"] = effective_days * mensual_wage * 1.10
        elif self.type == "sunday_overtime":
            result["extra_hours"] = effective_days * hour_value * 2.0
        elif self.type == "sick_leave":
            # --- Calcular rango ---
            event_start = self.date
            event_end = self.date_end
            overlap_start = max(event_start, payroll_start) if payroll_start else event_start
            overlap_end = min(event_end, payroll_end) if payroll_end else event_end

            if not (overlap_start and overlap_end and overlap_start <= overlap_end):
                result["sick"] = 0.0
                return result

            # --- Días efectivos en este período ---
            effective_days = (overlap_end - overlap_start).days + 1

            # --- Calcular offset: cuántos días pasaron antes del inicio de la nómina ---
            days_before_period = (overlap_start - event_start).days

            pago_total = 0
            for i in range(effective_days):
                dia_global = days_before_period + i + 1  # el día "real" dentro de la incapacidad

                if day_value_percentage > minimum_day_value:
                    # Regla especial: siempre desde el día 1 al 66.67%
                    if dia_global <= 90:
                        pago_total += day_value * 0.6667
                        _logger.info(f"{self.employee_id.name} lo cual es correcto :3")
                    elif 91 <= dia_global <= 180:
                        pago_total += day_value * 0.5
                    else:
                        raise ValueError("Incapacidad supera los 180 días.")
                else:
                    if dia_global <= 90:
                        pago_total += minimum_day_value
                    elif 91 <= dia_global <= 180:
                        pago_total += minimum_day_value * 0.5
                    else:
                        raise ValueError("Incapacidad supera los 180 días.")

            result["sick"] = pago_total
        elif self.type == "arl_leave":
            result["arl"] = effective_days * day_value * 1
        elif self.type == "night_surcharge":
            result["night_surcharge"] = effective_days * hour_value * 0.35
        elif self.type == "unpaid_leave":
            result["deductions"] = effective_days * day_value

        return result
