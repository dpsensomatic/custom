from odoo import fields, models, api
from datetime import timedelta
import ipdb
import logging

_logger = logging.getLogger(__name__)

class HrPayrollEvents(models.Model):
    # ===========================
    # Definición Del Modelo 
    # ===========================
    _name = 'hr.payroll.events'
    _description = 'Eventos de Nomina'
    # ==========================

    # ==========================
    # Campos Del Modelo 
    # ==========================
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato", compute ='_compute_field_contract', required=True)
    type = fields.Selection([
        ('commissions', 'Comisiones'), # Valor Fijo
        ('bounties', 'Bonificaciones'), # Valor Fijo
        ('sick_leave', 'Incapacidades'), # Fecha, Cantidad, Remunerado, Cuenta para los dias trabajados pero no para beneficios
        ('arl_leave', 'Incapacidad ARL'), # Fecha, Cantidad, Remunerado, Cuenta para los dias trabajados pero no para beneficios  
        ('paid_leave', 'Permiso Remunerado'), # Fecha, Cantidad, Remunerado, Cuenta para los dias trabajados pero no para beneficios
        ('unpaid_leave', 'Permiso No Remunerado'), # Fecha, Cantidad, No Remunerado, Cuenta para los dias trabajados y descuenta en beneficios
    ], string='Tipo de Novedad', required=True)
    fixed_value = fields.Monetary(
        string="Valor fijo",
        currency_field="company_currency_id",
    )
    date = fields.Date(string='Fecha de la Novedad', required=True)
    quantity = fields.Integer(string='Cantidad de dias de la novedad' , default = 1)
    date_end = fields.Date(string="Fecha fin", compute="_compute_field_date_end", store=True)
    unit = fields.Selection([
        ('day', 'Día'),
        ('unit', 'Unidad'),
        ('hour', 'Hora')
    ], string='Tipos de Unidad', default = 'day')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de la compañía',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    # ==========================


    # ==========================
    # Campos Computados Del Modelo
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


    # ==========================
    # Funciones del modelo 
    # ==========================

    # ==========================
    # Cálculo del valor de la novedad
    # ==========================
    def _compute_value(self, unpaid_days):
        self.ensure_one()

        # === Valida si tiene contrato en caso contrario retorna 0 en todos los valores ===
        if not self.contract_id:
            return {'days_worked': 0.0, 
                    'unpaid_days': 0.0,
                    'sick_leave': 0.0, 
                    'overtime_hours': 0.0,
                    'commissions': 0.0,
                    'other': 0.0
                    }
    # =========================
            
        # ==========================
        # Variables base para cálculos
        # ==========================
        
        # === Parametros salariales vigentes en la fecha de la novedad ===
        params = self.env["hr.payroll.mixin"]._get_parameter(self.date)
        minimum_wage = params.get("minimum_wage", 0.0)
        minimum_day_wage = minimum_wage/30
        
        # Variables del contrato del empleado
        wage = self.contract_id.wage 
        day_wage = wage / 30
        day_wage_66 = day_wage * 0.6667
        hour_wage = day_wage / 8
        


        # ========================
        # Diccionario base 
        # ========================
        result = {'days_worked': 0.0, 
                    'unpaid_days': 0.0,
                    'sick_leave': 0.0, 
                    'overtime_hours': 0.0,
                    'commissions': 0.0,
                    'other': 0.0
                    }
        # ========================


    # ========================
    # Cálculos según tipo de novedad 
    # ========================
        # === commissions = Aumentos al salario por valor de ventas ===
        if self.type == "commissions":
            
            result["commissions"] = self.fixed_value or 0.0
        
        # === bounties = Bonificaciones que no afectan los calculos de prima,cesantias y vacaciones ===
        if self.type == "bounties":
            
            result["other"] = self.fixed_value or 0.0
            
        
        # === sick_leave = Incapacidades por enfermedad ===
        elif self.type == "sick_leave":
            ipdb.set_trace()
            total_payment = 0
            for i in range(int(unpaid_days)):
                # dia_global = days_before_period + i + 1  # el día "real" dentro de la incapacidad
                if day_wage_66 > minimum_day_wage:
                    # Regla especial: siempre desde el día 1 al 66.67%
                    if i <= 2:
                        total_payment += day_wage * 1
                    elif i <= 90 and i > 2:
                        total_payment += day_wage * 0.6667
                    elif i >= 91:
                        total_payment += day_wage * 0.5
                else:
                    if i <= 90:
                        total_payment += minimum_day_wage   
                    elif i >= 91:
                        total_payment += minimum_day_wage * 0.5
                        
            result["sick_leave"] = total_payment
            
            
        # === arl_leave = Incapacidad Por ARL ===
        elif self.type == "arl_leave":
            total_payment = 0.0
            if wage < minimum_wage:
                total_payment = unpaid_days * minimum_day_wage * 1
            else:
                total_payment = unpaid_days * day_wage * 1
            
            result['sick_leave'] = total_payment
            
            
        # === paid_leave = Dias no trabajados remunerados ===           
        elif self.type == "paid_leave":
            
            result["sick_leave"] = unpaid_days * day_wage * 1
            
            
        # === unpaid_leave = Dias no trabajados no remunerados ===           
        elif self.type == "unpaid_leave":
            
            result["sick_leave"] = 0.0
            
        # === retorna los valores conseguidos en las novedades ===
        return result
        # ========================