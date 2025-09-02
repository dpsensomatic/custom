from odoo import fields, models
import ipdb


class HrPayrollEvents(models.Model):
    _name = 'hr.payroll.events'
    _description = 'Eventos de Nomina'
    employee_id = fields.Many2one(
        'hr.employee', string="Empleado", required=True)
    contract_id = fields.Many2one("hr.contract", string="Contrato")
    type = fields.Selection([
        ('commissions', 'Comisiones'),
        ('day_overtime', 'Hora Extra Diurna'),
        ('sunday_overtime', 'Hora Extra Dominical'),
        # ('sunday_day_overtime', 'Hora Extra Dominical Diurna'),
        # ('sunday_night_overtime', 'Hora Extra Dominical Nocturna'),
        # ('holiday_overtime', 'Hora Extra Festiva'),
        # ('holiday_day_overtime', 'Hora Extra Festiva Diurna'),
        # ('holiday_night_overtime', 'Hora Extra Festiva Nocturna'),
        ('night_overtime', 'Hora Extra Nocturna'),
        ('night_surcharge', 'Hora Recargo Nocturno'),
        ('sick_leave', 'Incapacidades'),
        ('arl_leave', 'Incapacidad ARL'),
        ('unpaid_leave', 'Permiso No Remunerado'),
        # ('paid_leave', 'Permiso Remunerado'),
        # ('maternity_leave', 'Licencia De Maternidad'),
        # ('paternity_leave', 'Licencia De Paternidad'),
        # ('penalties', 'Sanciones'),
        # ('night_bonus', 'Recargo Nocturno'),
        # ('sunday_night_bonus', 'Recargo Nocturno Dominical'),
                #         vals = ev.compute_value()
                # comissions += vals.get('comissions', 0.0)
                # arl_leave += vals.get('arl', 0.0)  
                # sick_leave += vals.get('sick', 0.0)       # más seguro con .get()
                # total_gross += vals.get('gross', 0.0)
                # total_deductions += vals.get('deductions', 0.0)
    ], string='Tipo de Novedad')
    date = fields.Date(string='Fecha de la Novedad')
    quantity = fields.Integer(string='Cantidad de dias de la novedad')
    unit = fields.Selection([('day', 'Día'),
                             ('unit', 'Unidad'),
                             ('hour', 'Hora')
                             ], string='Tipos de Unidad')

    def compute_value(self):
        """Devuelve {'gross': X, 'deductions': Y, ...} según el tipo de novedad"""
        self.ensure_one()

        if not self.contract_id:
            return {"gross": 0.0, "deductions": 0.0, 'sick': 0.0,
                    "overtime": 0.0, "night": 0.0, 'other': 0.0, 'arl': 0.0, 'comissions':0.0}

        salario_mensual = self.contract_id.wage
        valor_dia = salario_mensual / 30
        valor_hora = valor_dia / 8

        # Diccionario base
        result = {"extra_hours": 0.0, "deductions": 0.0, 'sick': 0.0,
                  "overtime": 0.0, "night": 0.0, 'other': 0.0, 'arl': 0.0, 'comissions':0.0}

    
        if self.type == "day_overtime":
            result["extra_hours"] = self.quantity * valor_hora * 1.25
        elif self.type == "night_overtime":
            result["extra_hours"] = self.quantity * valor_hora * 1.75
        elif self.type == "commissions":
            result["comissions"] = self.quantity * salario_mensual * 1.10
        elif self.type == "sunday_overtime":
            result["extra_hours"] = self.quantity * valor_hora * 2.0
        elif self.type == "sick_leave":
            if 3 <= self.quantity <= 89:
                result["sick"] = self.quantity * valor_dia * 0.6667
            elif 90 <= self.quantity <= 179:
                result["sick"] = self.quantity * valor_dia * 0.50
            elif self.quantity >= 180:
                result["sick"] = self.quantity * valor_dia * 0.10
            else:
                result["sick"] = self.quantity * valor_dia * 1
        elif self.type == "arl_leave":
            result["arl"] = self.quantity * valor_dia * 1
        elif self.type == "night_surcharge":
            result["night_surcharge"] = self.quantity * valor_hora * 0.35
        elif self.type == "unpaid_leave":
            result["deductions"] = self.quantity * valor_dia

        return result
