# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class HrWorkRota(models.Model):
    _name = 'hr.work.rota'
    _description = 'Rota / Rotación de trabajo'

    name = fields.Char(required=True)
    start_date = fields.Date(string="Fecha inicio rotación", required=True, default=fields.Date.context_today)
    rotation_length = fields.Integer(string="Largo rotación (semanas)", default=4, required=True)
    line_ids = fields.One2many('hr.work.rota.line', 'rota_id', string="Días por semana en la rotación")


class HrWorkRotaLine(models.Model):
    _name = 'hr.work.rota.line'
    _description = 'Registro de rotación (semana X -> día Y)'

    rota_id = fields.Many2one('hr.work.rota', required=True, ondelete='cascade')
    week_index = fields.Integer(string="Índice de semana (0..n-1)", required=True)
    dayofweek = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    ], string="Día de la semana", required=True)
    
        

    #   hr.payroll.py  
        # Codigo para traer los dias trabajados usando las rotaciones de los sabados 
        #    for emp in employees:
        #     contract = emp.contract_id
        #     if not contract:
        #         continue
            
        #     start = max(contract.date_start, self.date_start)
        #     end = min(contract.date_end or self.date_end, self.date_end)
        #     days_set = set()
    
        #     if end >= start:
        #         # 1) Días según calendario (normalmente L-V)
        #         if contract.resource_calendar_id:
        #             # _work_intervals_batch necesita datetimes con tz -> usamos context_timestamp
        #             start_dt = fields.Datetime.context_timestamp(self, Datetime.to_datetime(start))
        #             end_dt = fields.Datetime.context_timestamp(self, Datetime.to_datetime(end) + timedelta(days=1))
        #             intervals = contract.resource_calendar_id._work_intervals_batch(start_dt, end_dt)[False]
        #             cal_days = {i[0].date() for i in intervals}
    
        #             # Si existe rota, removemos sábados/domingos que vengan del calendario
        #             # (la rota decidirá qué sábados contar)
        #             if contract.rota_id:
        #                 cal_days = {d for d in cal_days if d.weekday() < 5}  # 0..4 => L-V
        #             days_set |= cal_days
    
        #         # 2) Días extra por rota (ej. sábados puntuales según patrón)
        #         if contract.rota_id:
        #             d0 = start
        #             while d0 <= end:
        #                 delta_days = (d0 - contract.rota_id.start_date).days
        #                 if delta_days >= 0:
        #                     week_index = (delta_days // 7) % contract.rota_id.rotation_length
        #                     found = contract.rota_id.line_ids.filtered(
        #                         lambda r: r.week_index == week_index and int(r.dayofweek) == d0.weekday()
        #                     )
        #                     if found:
        #                         days_set.add(d0)
        #                 d0 += timedelta(days=1)
    
        #     days = len(days_set)
    
        #     # =======================
        #     # Calcular month_days (máximo esperable) = unión calendario (filtro L-V si rota) + días de rota
        #     # =======================
        #     mdays = set()
    
        #     if contract.resource_calendar_id:
        #         month_start_dt = fields.Datetime.context_timestamp(self, Datetime.to_datetime(self.date_start))
        #         month_end_dt = fields.Datetime.context_timestamp(self, Datetime.to_datetime(self.date_end) + timedelta(days=1))
        #         month_intervals = contract.resource_calendar_id._work_intervals_batch(month_start_dt, month_end_dt)[False]
        #         cal_mdays = {i[0].date() for i in month_intervals}
        #         if contract.rota_id:
        #             cal_mdays = {d for d in cal_mdays if d.weekday() < 5}
        #         mdays |= cal_mdays
    
        #     if contract.rota_id:
        #         d0 = self.date_start
        #         while d0 <= self.date_end:
        #             delta_days = (d0 - contract.rota_id.start_date).days
        #             if delta_days >= 0:
        #                 week_index = (delta_days // 7) % contract.rota_id.rotation_length
        #                 found = contract.rota_id.line_ids.filtered(
        #                     lambda r: r.week_index == week_index and int(r.dayofweek) == d0.weekday()
        #                 )
        #                 if found:
        #                     mdays.add(d0)
        #             d0 += timedelta(days=1)
    
        #     month_days = len(mdays)
    
        #     # =======================
        #     # Resultado y guardado
        #     # =======================
        #     _logger.info("Días trabajados %s: %s", emp.name, sorted(list(days_set)))
        #     gross = (contract.wage / month_days) * days if month_days else 0.0
    
        #     lines.append({
        #         'payroll_id': self.id,
        #         'employee_id': emp.id,
        #         'contract_id': contract.id,
        #         'days_worked': days,
        #         'gross': gross,
        #         'deductions': 0.0,
        #     })
    
        # self.write({'line_ids': [(5, 0, 0)] + [(0, 0, vals) for vals in lines]})



    # HR.CONTRACT.PY
    # rota_id = fields.Many2one(
    #     'hr.work.rota',
    #     string="Rota de trabajo",
    #     help="Define la rotación de días trabajados (ej: sábados cada 4 semanas)."
    #     )
