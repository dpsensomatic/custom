# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
from collections import defaultdict
import ipdb
import logging
import ast
import json

_logger = logging.getLogger(__name__)

# ========================
# Definicion Del Modelo
# ========================
class HrPayroll(models.Model):
    
    # === Descripcion Del Modelo ===
    _name = "hr.payroll"
    _description = "Nómina"

    # === Campos del Modelo ===
    name = fields.Char(string="Nombre", required=True, default="Nómina")
    date_start = fields.Date(string="Fecha inicio", required=True)
    date_end = fields.Date(string="Fecha fin", required=True)
    line_vals = fields.Char(string="Lineas De Contabilidad")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('done', 'Cerrada'),
    ], string="Estado", readonly=True, default="draft")
    
    # === Campos especiales ===
    precomputed_lines_json = fields.Text(string="Líneas contables precalculadas", copy=False)
    
    # === Campos Many ===
    line_ids = fields.One2many(
        "hr.payroll.line", 
        "payroll_id", 
        string="Líneas de nómina"
    )
    account_line_ids = fields.One2many(
        "hr.payroll.account.line",
        "payroll_id",
        string="Líneas contables"
    )
    total_debit = fields.Monetary(
        string='Total Débito',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_credit = fields.Monetary(
        string='Total Crédito',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    move_id = fields.Many2one(
        'account.move', 
        string='Asiento contable', 
        readonly=True, 
        copy=False
        )
    employee_selector_id = fields.Many2one(
        'hr.employee',
        string='Consultar por empleado',
        help='Selecciona un empleado vigente en este periodo de nómina.'
    )    

# ========================
    
    
    # ========================
    # Helpers pequeños
    # ========================
    def _empty_totals(self):
        """Diccionario base con todas las claves que usamos.
        Si agregas nuevos componentes, añádelos aquí."""
        return { 
                # === Datos Del Empleado Y Contrato ===
                'employee_id':0.0,
                'contract_id': 0.0,
                'base_wage': 0.0,
                
                # === Salario Ajustado Por Las Novedades ===
                'wage_earned': 0.0,
                'days_worked': 0.0,
                'unpaid_days': 0.0,
                'sick_leave': 0.0,
                'overtime_hours': 0.0,
                'transportation_allowance': 0.0,
                'commissions': 0.0,
                'other':0.0,
                'parafiscal_base': 0.0,
                'gross': 0.0,
                
                # === Aportes A Seguridad Social ===
                'health_contribution':0.0,
                'pension_contribution':0.0,
                'company_health_contribution':0.0,
                'company_pension_contribution':0.0,
                'arl_contribution':0.0,
                'other_deductions':0.0,
                
                'deductions':0.0,
                'total_deductions':0.0,
                
                # === Pagos A Prestaciones Sociales ===
                'service_bonus':0.0,
                'severance':0.0,
                'interest_on_severance':0.0,
                'vacations':0.0,
                'total_provisions':0.0,
                
                # === Totales A Pagar ===
                # Pago Empleado
                'net':0.0,
                # Pago Empresa
                'total_net':0.0,
        }
    # ========================
    
    
    def _empty_total_accounts(self):
        return { 
                # === Totales acumulados ===
                'wages_debit' : 0.0,
                'wages_credit': 0.0,
                'commissions': 0.0,
                'incapacity': 0.0,
                'transport': 0.0,
                
                # === Seguridad Social ===
                'health_debit': 0.0,
                'pension_debit': 0.0,
                'arl_debit': 0.0,
                
                # === Beneficios ===
                'service_bonus_debit': 0.0,
                'service_bonus_credit': 0.0,
                'severance_debit': 0.0,
                'severance_credit': 0.0,
                'interest_debit': 0.0,
                'interest_credit': 0.0,
                'vacations_debit': 0.0,
                'vacations_credit': 0.0,
        }
    

    # ========================
    # Acción principal (Genera Las Lineas De La Nomina)
    # ========================
    def action_generate_lines(self):
        self.ensure_one()

        # ========================
        # Verifica que se hayan elegido las fechas de nomina
        # ========================
        if not self.date_start or not self.date_end:
            raise UserError("Debe definir las fechas de inicio y fin.")
        # ========================
        
        
        # ========================
        # Trae Todos los empleados con sus contratos
        # ========================
        
        # === Trae Todos Los Empleado Creados En Hr_Employee ===
        employees = self.env['hr.payroll.mixin']._get_employees_with_contracts(self.date_start, self.date_end)
        lines = []

        # === Hace El Bucle De los Empleados Y Sus Respectivos Contratos ===
        for employee, contract in employees.items():

            # === Trae Los Eventos Por Empleado Segun Fecha De La Nomina ===
             
            events = self.env['hr.payroll.mixin']._get_events(employee.id, self.date_start, self.date_end)
            parameters = self.env['hr.payroll.mixin']._get_parameter(self.date_start)
            # === Ajustamos los parametros  ===
            transportation_allowance = parameters['transport_allowance']
            company_pension_percentage = parameters['company_pension_percentage']
            company_health_percentage = parameters['company_eps_percentage']
            employee_eps_percentage = parameters['employee_eps_percentage']
            employee_pension_percentage = parameters['employee_pension_percentage']
            minimun_wage = parameters['minimum_wage']

            # === Vacia Los Totales Del Diccionario Con Cada Ciclo ===            
            totals = self._empty_totals()


            # === Calculo De Los Dias Trabajados ===
            totals = self.env['hr.payroll.mixin']._compute_days_worked(events, totals,  self.date_start, self.date_end)

            # === Calculo De Los Eventos Sin Incapacidad
            incapacity_types = ['sick_leave', 'unpaid_leave', 'arl_leave']
            events_worked =  events.filtered(lambda e: e.type not in incapacity_types)
            if events_worked:
                for ev in events_worked:
                    vals = ev._compute_value(totals['unpaid_days']) or {}
                for k, v in vals.items():
                    try:
                        totals[k] = totals.get(k, 0.0) + float(v or 0.0)
                    except Exception:
                        pass

            # === Calculo del Salario segun incapacidades ===
            totals['wage_earned'] = contract.wage * (totals['days_worked'] / 30)
            totals['parafiscal_base'] = totals['wage_earned'] + totals['commissions'] + totals['overtime_hours']
            transport_base = totals['parafiscal_base'] 
            
            # === Calculo Auxilio De Transporte ===
            totals['transportation_allowance'] = self.env['hr.payroll.mixin']._compute_transport_allowance(
                transport_base, totals['days_worked'], minimun_wage, transportation_allowance
            )

            # === Total A Pagar Al Trabajador ===
            totals['gross'] = self.env['hr.payroll.mixin']._compute_total_gross(totals)

            # === Aportes A Seguridad Social (Salud, Pension, ARL) ===
            totals = self.env['hr.payroll.mixin']._compute_contributions(
                totals,
                company_health_percentage,
                employee_eps_percentage,
                company_pension_percentage,
                employee_pension_percentage,
                minimun_wage,
                contract,
            )

            # === Aportes A Prestaciones Sociales (Prima, Cesantias, Vacaciones) ===
            # === Filtra Todos Los Eventos Que Pertenezcan A Incapacidades ===
            allowed_types = ['unpaid_leave']
            events =  events.filtered(lambda e: e.type in allowed_types)

            if events:
                # === Se Seccionan Las Fechas Y Se Traen Los Totales De Dias De Incapacidad ===
                split_dates = self.env['hr.payroll.mixin']._split_event_dates(events, self.date_start, self.date_end)


                totals['unpaid_days'] = self.env['hr.payroll.mixin']._compute_all_unpaid_days(split_dates)
                totals['unpaid_leaves'] = self.env['hr.payroll.mixin']._adjust_days_worked(split_dates, totals['unpaid_days'])
            else:
                totals['unpaid_leaves'] = 30
                
            totals = self.env['hr.payroll.mixin']._compute_benefits(totals, totals['unpaid_leaves'])


            # === Totales De Aportes A Seguridad Social (Salud, Pension, ARL) ===
            # Total A Pagar Trabajador
            totals['deductions'] = totals['health_contribution'] + totals['pension_contribution']
            

            # Total A Pagar Empleador
            totals['total_deductions'] = totals['deductions'] + totals['arl_contribution']

            # ========================

            # ========================
            # Crea Las Lineas Con La Informacion Recolectada
            # ========================
            vals_line = {
                # === Datos Del Empleado Y Contrato ===
                'employee_id': employee.id,
                'contract_id': contract.id,
                'base_wage': contract.wage,

                # === Salario Ajustado Por Las Novedades ===
                'wage_earned': totals['wage_earned'],
                'days_worked': totals['days_worked'],
                'sick_leave': totals['sick_leave'],
                'overtime_hours': totals['overtime_hours'],
                'transportation_allowance': totals['transportation_allowance'],
                'commissions': totals['commissions'],
                'other': totals['other'],
                'gross': totals['gross'],

                # === Aportes A Seguridad Social ===
                'health_contribution': totals['health_contribution'],
                'pension_contribution': totals['pension_contribution'],
                'company_health_contribution': totals['company_health_contribution'],
                'company_pension_contribution': totals['company_pension_contribution'],
                'arl_contribution': totals['arl_contribution'],
                'other_deductions': 0.0,

                'deductions': totals['deductions'],
                'total_deductions': totals['total_deductions'],

                # === Pagos A Prestaciones Sociales ===
                'service_bonus': totals['service_bonus'],
                'severance': totals['severance'],
                'interest_on_severance': totals['interest_on_severance'],
                'vacations': totals['vacations'],
                'total_provisions': totals['total_provisions'],

                # === Totales A Pagar ===
                # Pago Empleado
                'net': totals['gross'] - totals['deductions'],
                # Pago Empresa
                'total_net': totals['gross'] + totals['total_deductions'],
            }

            # ===  ===
            lines.append((0, 0, vals_line))

        # ===  ===
        self.line_ids = [(5, 0, 0)] + lines
    # ========================
    

    # ========================
    # Genera Los Apuntes Contables
    # ========================    
    def action_generate_accounting_entries(self):
        """Crea o actualiza líneas contables totales de la nómina."""
        for payroll in self:
            payroll.account_line_ids.unlink()


            
            totals_account = self._compute_total_accounts()

            
            # === Creación de líneas contables ===
            # === Creación de líneas contables ===
            line_vals = []

            # Líneas de cuentas normales
            line_vals += payroll._configure_accounting_lines(totals_account, payroll)

            # Líneas de aportes (EPS, pensión, ARL)
            line_vals += payroll._configure_contribution_lines(payroll)

            # Línea de ajuste (si es necesario)
            line_vals = payroll._rounding_method(line_vals, payroll)
        
            payroll.precomputed_lines_json = json.dumps(line_vals)
            
            # Crear todas las líneas
            self.env['hr.payroll.account.line'].create(line_vals)
    # ========================
    

    # ========================
    # Trae El Empleado Seleccionado Y Consulta Sus Cuentas Contables
    # ========================
    def action_filter_by_employee(self):
        self.ensure_one()
        if not self.employee_selector_id:
            raise UserError("Por favor selecciona un empleado antes de consultar.")
    
        # Borramos las líneas previas
        self.account_line_ids.unlink()
    
        # Recalculamos solo para ese empleado
        employee_lines = self.line_ids.filtered(lambda l: l.employee_id == self.employee_selector_id)
        if not employee_lines:
            raise UserError("No hay líneas de nómina para el empleado seleccionado en este periodo.")  
        # Creamos las líneas filtradas
        
        
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_selector_id.id),
            ('state', '=', 'open')
        ], limit=1)
        accounts_model = self.env['hr.predetermined.accounts']
        acc_config = accounts_model.search([('company_id', '=', self.env.company.id)], limit=1)
        
        pension_credit = employee_lines.company_pension_contribution + employee_lines.pension_contribution
        # === Creación de líneas contables ===

        line_vals = []
    # =======================
    # Crea a Tabla Con Los Valores En La Nómina 
    # =======================
        # =======================
        #  eneficios Credito
        # =======================
        # === Prima De Servicios === 
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Prima De Servicios Credito',
            'account_id': acc_config.service_bonus_account_credit.id,
            'debit': 0.0,
            'credit': employee_lines.service_bonus,
        })
        
        # === Cesantias ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Cesantias Credito',
            'account_id': acc_config.severance_account_credit.id,
            'debit': 0.0,
            'credit': employee_lines.severance,
        })
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Intereses Sobre Cesantias Credito',
            'account_id': acc_config.severance_interest_account_credit.id,
            'debit': 0.0,
            'credit': employee_lines.interest_on_severance,
        })
        
        # === Vacaciones ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Vacaciones Credito',
            'account_id': acc_config.vacation_account_credit.id,
            'debit': 0.0,
            'credit': employee_lines.vacations,
        })
        # ========================
        
        
        # =======================
        # Debito
        # =======================
        # === Sueldos ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Sueldos Debito',
            'account_id': acc_config.wage_account_debit.id,
            'debit': employee_lines.wage_earned,
            'credit': 0.0,
        })
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Comisiones',
            'account_id': acc_config.commission_account_debit.id,
            'debit': employee_lines.commissions,
            'credit': 0.0,
        })
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Incapacidad',
            'account_id': acc_config.arl_incapacity_account_debit.id,
            'debit': employee_lines.sick_leave,
            'credit': 0.0,
        })
        
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Auxilio Transporte',
            'account_id': acc_config.transport_allowance_account_debit.id,
            'debit': employee_lines.transportation_allowance,
            'credit': 0.0,
        })
        
          #=== Aportes A Seguridad Social ===
        # === Aportes A Salud ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aporte A Salud Debito',
            'account_id': acc_config.health_account_debit.id,
            'debit': employee_lines.company_health_contribution,
            'credit': 0.0, 
        })
        
        # === Aportes A Pension ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aportes Pensión Debito',
            'account_id': acc_config.pension_account_debit.id,
            'debit': employee_lines.company_pension_contribution,
            'credit': 0.0,
        })
        
        # === Aportes A Arl === 
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aportes A Arl Debit',
            'account_id': acc_config.arl_account_debit.id,
            'debit': employee_lines.arl_contribution,
            'credit': 0.0,
        })
                    
          #=== Beneficios ===   
        
        # === Prima De Servicios ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Prima De Servicios Debito',
            'account_id': acc_config.service_bonus_account_debit.id,
            'debit': employee_lines.service_bonus,
            'credit': 0.0,
        })
        
        # === Cesantias ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Cesantias Debito',
            'account_id': acc_config.severance_account_debit.id,
            'debit': employee_lines.severance,
            'credit': 0.0,
        })
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Intereses Sobre Cesantias Debito',
            'account_id': acc_config.severance_interest_account_debit.id,
            'debit': employee_lines.interest_on_severance,
            'credit': 0.0,
        })
        
        # === Vacaciones ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Vacaciones Debito',
            'account_id': acc_config.vacation_account_debit.id,
            'debit': employee_lines.vacations,
            'credit': 0.0,
        })
        # =======================        
    
    
        # =======================
        # Cedito 
        # =======================        
        # === Sueldos ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Sueldos Credito',
            'account_id': acc_config.wage_account_credit.id,
            'debit': 0.0,
            'credit': employee_lines.net,
        })
        
          #=== Aportes A Seguridad Social ===
        
        # === Aportes A Salud ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aporte A Salud Credito',
            'account_id': contract.eps_id.eps_account.id,
            'debit': 0.0,
            'credit': employee_lines.health_contribution, 
        })
        
        # === Aportes A Pension ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aportes Pensión Credito',
            'account_id': contract.pension_fund_id.pension_account.id,
            'debit': 0.0,
            'credit': pension_credit,
        })
        
        # === Aportes A Arl ===
        line_vals.append({
            'payroll_id': employee_lines.payroll_id.id,
            'concept_name': 'Aportes A Arl Credit',
            'account_id': contract.arl_id.arl_account.id,
            'debit': 0.0,
            'credit': employee_lines.arl_contribution,
        })
        total_debit = sum(line['debit'] for line in line_vals)
        total_credit = sum(line['credit'] for line in line_vals)
        difference = round(total_debit - total_credit, 2)

        if abs(difference) >= 0.01:
            # Determina si hay más débito o crédito
            adjust_type = 'debit' if difference < 0 else 'credit'
            adjust_value = abs(difference)
            
            # Añade línea de ajuste al diario para cuadrar el asiento
            line_vals.append({
                'payroll_id': employee_lines.payrrol_id.id,
                'concept_name': 'Ajuste Por Redondeo',
                'account_id': acc_config.rounding_credit.id or acc_config.rounding_debit.id,
                'debit': adjust_value if adjust_type == 'debit' else 0.0,
                'credit': adjust_value if adjust_type == 'credit' else 0.0,
            })   
            ipdb.set_trace()
          
        self.env['hr.payroll.account.line'].create(line_vals)
    # ========================
    
    
    # ========================
    # Computa Los Totales De Debito Y Credito
    # ========================
    @api.depends('account_line_ids.debit', 'account_line_ids.credit')
    def _compute_totals(self):
        for rec in self:
            rec.total_debit = sum(rec.account_line_ids.mapped('debit'))
            rec.total_credit = sum(rec.account_line_ids.mapped('credit'))
    # ========================
    
    
    # ========================
    # Extrae Los Valores De La Nomina Generada Y Genera Los Totales
    # ========================
    def _compute_total_accounts(self):
        """Calcula los totales de todas las cuentas con base en las líneas de nómina."""
        self.ensure_one()  # buena práctica: solo debe aplicarse a un registro

        totals = self._empty_total_accounts()
        currency = self.currency_id

        # === Totales acumulados ===
        totals['wages_debit'] = currency.round(sum(line.wage_earned for line in self.line_ids))
        totals['wages_credit'] = currency.round(sum(line.net for line in self.line_ids))
        totals['commissions'] = currency.round(sum(line.commissions for line in self.line_ids))
        totals['incapacity'] = currency.round(sum(line.sick_leave for line in self.line_ids))
        totals['transport'] = currency.round(sum(line.transportation_allowance for line in self.line_ids))

        # === Seguridad Social ===
        totals['health_debit'] = currency.round(sum(line.company_health_contribution for line in self.line_ids))
        totals['pension_debit'] = currency.round(sum(line.company_pension_contribution for line in self.line_ids))
        totals['arl_debit'] = currency.round(sum(line.arl_contribution for line in self.line_ids))

        # === Beneficios ===
        totals['service_bonus_debit'] = currency.round(sum(line.service_bonus for line in self.line_ids))
        totals['service_bonus_credit'] = totals['service_bonus_debit']
        totals['severance_debit'] = currency.round(sum(line.severance for line in self.line_ids))
        totals['severance_credit'] = totals['severance_debit']
        totals['interest_debit'] = currency.round(sum(line.interest_on_severance for line in self.line_ids))
        totals['interest_credit'] = totals['interest_debit']
        totals['vacations_debit'] = currency.round(sum(line.vacations for line in self.line_ids))
        totals['vacations_credit'] = totals['vacations_debit']
        
        return totals
    # ========================
    
     
    # ========================
    # Extrae Valores De Los Aportes Y Genera Los Totales
    # ========================
    def _configure_contribution_lines(self, payroll):
        line_vals = []
        currency = self.currency_id

        acc_config = self.env['hr.predetermined.accounts'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not acc_config:
            return []

        totales_por_cuenta = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'concept_name': ''})

        for line in payroll.line_ids:
            contract = line.contract_id

            # === Salud Crédito ===
            cuenta_salud = contract.eps_id.eps_account.id or acc_config.health_account_credit.id
            totales_por_cuenta[cuenta_salud]['credit'] += currency.round(line.health_contribution)
            totales_por_cuenta[cuenta_salud]['concept_name'] = 'Aportes A Salud Credito'

            # === Pensión Crédito ===
            cuenta_pension = contract.pension_fund_id.pension_account.id or acc_config.pension_account_credit.id
            totales_por_cuenta[cuenta_pension]['credit'] += currency.round((
                line.pension_contribution + line.company_pension_contribution
            ))
            totales_por_cuenta[cuenta_pension]['concept_name'] = 'Aportes Pensión Credito'

            # === ARL Crédito ===
            cuenta_arl = contract.arl_id.arl_account.id or acc_config.arl_account_credit.id
            totales_por_cuenta[cuenta_arl]['credit'] += currency.round(line.arl_contribution)
            totales_por_cuenta[cuenta_arl]['concept_name'] = 'Aportes A Arl Credito'

        # Convertir diccionario a lista de líneas
        for cuenta_id, datos in totales_por_cuenta.items():
            if not cuenta_id:
                continue
            line_vals.append({
                'payroll_id': payroll.id,
                'concept_name': datos['concept_name'],
                'account_id': cuenta_id,
                'debit': 0.0,
                'credit': datos['credit'],
            })

        return line_vals
    # ========================
    
    
    # ========================
    # Ajusta Las Lineas Con Los Totales Dados
    # ========================
    def _configure_accounting_lines(self,totals,payroll):
        line_vals = []
        accounts_model = self.env['hr.predetermined.accounts']
        acc_config = accounts_model.search([('company_id', '=', self.env.company.id)], limit=1)
        if not acc_config:
            return []
        
        # ========================
        #  Beneficios Credito
        # ========================
        # === Prima De Servicios === 
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Prima De Servicios Credito',
        'account_id': acc_config.service_bonus_account_credit.id,
        'debit': 0.0,
        'credit': totals['service_bonus_credit'],
        })
        
        # === Cesantias ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Cesantias Credito',
        'account_id': acc_config.severance_account_credit.id,
        'debit': 0.0,
        'credit': totals['severance_credit'],
        })
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Intereses Sobre Cesantias Credito',
        'account_id': acc_config.severance_interest_account_credit.id,
        'debit': 0.0,
        'credit': totals['interest_credit'],
        })
        
        # === Vacaciones ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Vacaciones Credito',
        'account_id': acc_config.vacation_account_credit.id,
        'debit': 0.0,
        'credit': totals['vacations_credit'],
        })
        # ========================
        
        
        # ========================
        # Debito
        # ========================
        # === Sueldos ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Sueldos Debito',
        'account_id': acc_config.wage_account_debit.id,
        'debit': totals['wages_debit'],
        'credit': 0.0,
        })
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Comisiones',
        'account_id': acc_config.commission_account_debit.id,
        'debit': totals['commissions'],
        'credit': 0.0,
        })
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Incapacidad',
        'account_id': acc_config.arl_incapacity_account_debit.id,
        'debit': totals['incapacity'],
        'credit': 0.0,
        })
        
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Auxilio Transporte',
        'account_id': acc_config.transport_allowance_account_debit.id,
        'debit': totals['transport'],
        'credit': 0.0,
        })
        
        # === Aportes A Seguridad Social ===
# === Aportes A Salud ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Aporte A Salud Debito',
        'account_id': acc_config.health_account_debit.id,
        'debit': totals['health_debit'],
        'credit': 0.0, 
        })
        
        # === Aportes A Pension ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Aportes Pensión Debito',
        'account_id': acc_config.pension_account_debit.id,
        'debit': totals['pension_debit'],
        'credit': 0.0,
        })
        
        # === Aportes A Arl === 
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Aportes A Arl Debit',
        'account_id': acc_config.arl_account_debit.id,
        'debit': totals['arl_debit'],
        'credit': 0.0,
        })
        
          # === Beneficios ===   
          
        # === Prima De Servicios ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Prima De Servicios Debito',
        'account_id': acc_config.service_bonus_account_debit.id,
        'debit': totals['service_bonus_debit'],
        'credit': 0.0,
        })
        
        # === Cesantias ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Cesantias Debito',
        'account_id': acc_config.severance_account_debit.id,
        'debit': totals['severance_debit'],
        'credit': 0.0,
        })
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Intereses Sobre Cesantias Debito',
        'account_id': acc_config.severance_interest_account_debit.id,
        'debit': totals['interest_debit'],
        'credit': 0.0,
        })
        
        # === Vacaciones ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Vacaciones Debito',
        'account_id': acc_config.vacation_account_debit.id,
        'debit': totals['vacations_debit'],
        'credit': 0.0,
        })
        # ========================        
        
        
        # ========================
        # Credito 
        # ========================        

        # === Sueldos ===
        line_vals.append({
        'payroll_id': payroll.id,
        'concept_name': 'Sueldos Credito',
        'account_id': acc_config.wage_account_credit.id,
        'debit': 0.0,
        'credit': totals['wages_credit'],
        })
            
        return line_vals
    # ========================


    # ========================
    # Redondea Los Decimales 
    # ========================
    def _rounding_method(self, lines_vals, payroll):
        """Ajuste por redondeo si los débitos y créditos no cuadran."""
        acc_config = self.env['hr.predetermined.accounts'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not acc_config:
            return lines_vals

        total_debit = sum(line['debit'] for line in lines_vals)
        total_credit = sum(line['credit'] for line in lines_vals)
        difference = round(total_debit - total_credit, 2)

        if abs(difference) >= 0.01:
            adjust_type = 'debit' if difference < 0 else 'credit'
            adjust_value = abs(difference)

            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Ajuste por redondeo',
                'account_id': acc_config.rounding_credit.id or acc_config.rounding_debit.id,
                'debit': adjust_value if adjust_type == 'debit' else 0.0,
                'credit': adjust_value if adjust_type == 'credit' else 0.0,
            })

        return lines_vals
    # ========================
    
    
    # ========================
    # Confirma Los Asientos Contables Y Los Guarda En account.move
    # ========================
    def action_confirm(self):
        for payroll in self:
            
            if not payroll.precomputed_lines_json:
                raise UserError('Genere la nomina y las cuentas contables')

            line_vals = json.loads(payroll.precomputed_lines_json or "[]")
            if not line_vals:
                continue
            
            # === Trae Los Campos Existentes Dentro De 'account.move.line' ===
            valid_fields = self.env['account.move.line']._fields.keys()
            # 
            # === Deja Solo Los Campos Necesarios Para La Creacion Del Asiento ===
            clean_line_vals = []
            for line in line_vals:
                clean_line = {k: v for k, v in line.items() if k in valid_fields}
                clean_line_vals.append((0, 0, clean_line))
            
            journal = self.env['account.journal'].search([('type', '=', 'general'), ('name', 'ilike', 'Nomina')], limit=1) 
            if not journal:
                raise UserError("Debe crear un diario en facturacion de tipo varios y nombre Nomina.")
            # Crea el asiento contable
            
            if payroll.move_id:
                move = payroll.move_id
                # Si está publicado, primero lo pasamos a borrador
                if move.state == 'posted':
                    move.button_draft()

                    # Borrar líneas viejas y escribir las nuevas
                    move.line_ids.unlink()
                    move.write({
                        'journal_id': journal.id,
                        'date': payroll.date_end,
                        'ref': payroll.name,
                        'line_ids': clean_line_vals,
                    })
            else:
                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'date' : payroll.date_end,
                    'ref': payroll.name,
                    'line_ids': clean_line_vals,
                })
                payroll.move_id = move.id
                
            move.action_post()
            payroll.state ='confirmed'
    # ========================
    
    
    # ========================
    # Actualiza Los Asientos Contables A Estado Draft  
    # ========================
    def action_reset_to_draft(self):
        for payroll in self:
            if payroll.move_id and payroll.move_id.state == 'posted':
                payroll.move_id.button_draft()
            payroll.state = 'draft'
    # ========================