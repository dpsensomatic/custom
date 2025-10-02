from odoo import fields, models, api
from datetime import timedelta
import ipdb
import logging

_logger = logging.getLogger(__name__)

class HrPayrollEvents(models.Model):
    # ===========================
    # == Definición del modelo ==
    # ===========================
    _name = 'hr.payroll.events'
    _description = 'Eventos de Nomina'
    # ==========================

    # ==========================
    # === Campos del modelo ===
    # ==========================
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", compute ='_compute_field_contract')
    type = fields.Selection([
        ('commissions', 'Comisiones'),
        ('day_ot_25', 'Hora Extra Diurna 25%'),
        ('night_shift_35', 'Hora nocturno 35%'),
        ('night_ot_75', 'Hora extra nocturno 75%'),
        ('holiday_80', 'Hora dominical y festivo 80%'),
        ('holiday_day_ot_105', 'Hora extra diurno dominical y festivo 105%'),
        ('holiday_night_115', 'Hora nocturno en dominical y festivo 115%'),
        ('holiday_night_ot_155', 'Hora extra nocturno en domingos y festivos 155%'),
        ('night_surcharge', 'Hora Recargo Nocturno'),
        ('sick_leave', 'Incapacidades'),
        ('arl_leave', 'Incapacidad ARL'),
        ('unpaid_leave', 'Permiso No Remunerado'),
    ], string='Tipo de Novedad')
    date = fields.Date(string='Fecha de la Novedad')
    date_end = fields.Date(string="Fecha fin", compute="_compute_field_date_end", store=True)
    quantity = fields.Integer(string='Cantidad de dias de la novedad')
    unit = fields.Selection([
        ('day', 'Día'),
        ('unit', 'Unidad'),
        ('hour', 'Hora')
    ], string='Tipos de Unidad')
    # ==========================

    # ==========================
    # Calculo del campo contract_id
    # ==========================
    @api.depends('employee_id')
    def _compute_field_contract(self):
        # Método que asigna el contrato del empleado al campo contract_id
        for record in self:
            if record.employee_id and record.employee_id.contract_id:
                record.contract_id = record.employee_id.contract_id
            else:
                record.contract_id = False
    # ==========================

    # ==========================
    # Cálculo del campo date_end
    # ==========================
    @api.depends("date", "quantity")
    def _compute_field_date_end(self):
        # El campo date_end se calcula automáticamente sumando la cantidad de días (quantity) a la fecha de inicio (date).
        for record in self:
            if record.date and record.quantity:
                record.date_end = record.date + timedelta(days=record.quantity - 1)
            else:
                record.date_end = record.date
    # ==========================

    # ==========================
    # Cálculo del valor de la novedad
    # ==========================
    def _compute_value(self, days_worked):
        # Método que calcula el valor de la novedad, recibe 3 parámetros
        # - self: el registro actual de hr.payroll.events
        # - payroll_start: fecha de inicio del período de nómina (opcional)
        # - payroll_end: fecha de fin del período de nómina (opcional)
        # Devuelve {'gross': X, 'deductions': Y, ...} según el tipo de novedad.
        # Si payroll_start y payroll_end están definidos, solo cuenta los días dentro de ese rango.
        self.ensure_one()

        # Valida si tiene contrato en caso contrario retorna 0 en todos los valores
        if not self.contract_id:
            return {
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'night_surcharge': 0.0,
                'other_earnings':0.0,
                'gross': 0.0,
                'net':0.0,
                }
    # =========================
            
        # ==========================
        # Variables base para cálculos
        # ==========================
        # Parametros salariales vigentes en la fecha de la novedad
        params = self.env["hr.parameters"].get_parameters_for_date(self.date)
        minimum_wage = params.get("minimum_wage", 0.0)
        minimum_day_wage = minimum_wage/30
        
        # Variables del contrato del empleado
        wage = self.contract_id.wage 
        day_wage = wage / 30
        day_wage_66 = day_wage * 0.6667
        hour_wage = day_wage / 8
        
        # === Calcular días efectivos ===
        month_days = 30
        month_days -= days_worked
        # ==========================


        # ========================
        # === Diccionario base ===
        # ========================
        result = {"extra_hours": 0.0,
                  "deductions": 0.0,
                  'sick': 0.0,
                  "arl": 0.0,
                  'comissions': 0.0,
                  'night_surcharge': 0.0,
                  'other': 0.0
                  }
        # ========================

        # ========================
        # Cálculos según tipo de novedad 
        # ========================
        # === Calculos de Horas Extras ===
        if self.type == "day_overtime":
            result["extra_hours"] = month_days * hour_wage * 1.25
        elif self.type == "night_overtime":
            result["extra_hours"] = month_days * hour_wage * 1.75
        elif self.type == "commissions":
            result["comissions"] = month_days * wage * 1.10
        elif self.type == "sunday_overtime":
            result["extra_hours"] = month_days * hour_wage * 2.0
        
        # === sick_leave = Incapacidades de otro tipo ===
        elif self.type == "sick_leave":
            ipdb.set_trace()
            total_payment = 0
            for i in range(month_days):
                # dia_global = days_before_period + i + 1  # el día "real" dentro de la incapacidad
                if day_wage_66 > minimum_day_wage:
                    # Regla especial: siempre desde el día 1 al 66.67%
                    if i <= 90:
                        total_payment += day_wage * 0.6667
                    elif i >= 91:
                        total_payment += day_wage * 0.5
                else:
                    if i <= 90:
                        total_payment += minimum_day_wage   
                    elif i >= 91:
                        total_payment += minimum_day_wage * 0.5

            result["sick"] = total_payment
            
        # === arl_leave = Incapacidad Por ARL ===
        elif self.type == "arl_leave":
            total_payment = 0.0
            if wage < minimum_wage:
                total_payment = month_days * minimum_day_wage * 1
            else:
                total_payment = month_days * day_wage * 1
            
            result["arl"] = total_payment
            
        # === Recargo nocturno ===
        elif self.type == "night_surcharge":
            result["night_surcharge"] = month_days * hour_wage *  0.35
            
        # === unpaid_leave = Dias no trabajados no remunerados            
        elif self.type == "unpaid_leave":
            result["deductions"] = month_days * day_wage

        # === retorna los valores conseguidos en las novedades ===
        return result
        # ========================