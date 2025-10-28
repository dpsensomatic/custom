# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import ipdb
import logging


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
    ], string="Estado", default="draft")
    
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
    # Genera Los Apuntes Contables
    # ========================    
    def action_generate_accounting_entries(self):
        """Crea o actualiza líneas contables totales de la nómina."""
        for payroll in self:
            payroll.account_line_ids.unlink()

            accounts_model = self.env['hr.predetermined.accounts']
            acc_config = accounts_model.search([('company_id', '=', self.env.company.id)], limit=1)
            if not acc_config:
                continue
            ipdb.set_trace()
            # === Totales acumulados ===
            wages_debit = self.currency_id.round(sum(line.wage_earned for line in payroll.line_ids))#check
            wages_credit = self.currency_id.round(sum(line.net for line in payroll.line_ids)) #check
            commissions = self.currency_id.round(sum(line.commissions for line in payroll.line_ids)) #check
            incapacity  = self.currency_id.round(sum(line.sick_leave for line in payroll.line_ids))  #check
            transport = self.currency_id.round(sum(line.transportation_allowance for line in payroll.line_ids)) #check

            # === Seguridad Social ===
            health_debit = self.currency_id.round(sum(line.company_health_contribution for line in payroll.line_ids)) #check
            health_credit = self.currency_id.round(sum(line.health_contribution for line in payroll.line_ids)) #check
            pension_debit = self.currency_id.round(sum(line.company_pension_contribution for line in payroll.line_ids)) #check
            pension_credit = self.currency_id.round(sum(payroll.line_ids.mapped('pension_contribution')) + sum(payroll.line_ids.mapped('company_pension_contribution'))) #check
            arl_debit = self.currency_id.round(sum(line.arl_contribution for line in payroll.line_ids)) #check
            arl_credit = self.currency_id.round(sum(line.arl_contribution for line in payroll.line_ids)) #check
            
            # === Beneficios ===
            service_bonus_debit = self.currency_id.round(sum(line.service_bonus for line in payroll.line_ids)) #check
            service_bonus_credit = self.currency_id.round(sum(line.service_bonus for line in payroll.line_ids)) #check
            severance_debit = self.currency_id.round(sum(line.severance for line in payroll.line_ids)) #check
            severance_credit = self.currency_id.round(sum(line.severance for line in payroll.line_ids)) #check
            interest_debit = self.currency_id.round(sum(line.interest_on_severance for line in payroll.line_ids)) #check
            interest_credit = self.currency_id.round(sum(line.interest_on_severance for line in payroll.line_ids)) #check
            vacations_debit = self.currency_id.round(sum(line.vacations for line in payroll.line_ids)) #check
            vacations_credit = self.currency_id.round(sum(line.vacations for line in payroll.line_ids)) #check

            # wages_debit 
            # commissions
            # incapacity
            # transport
            # health_debit
            # pension_debit
            
            # wages_credit
            # pension_credit
            # health_credit
            
            # === Creación de líneas contables ===
            lines_vals = []
    # ========================
    # Crea La Tabla Con Los Valores En La Nómina 
    # ========================
        # ========================
        #  Beneficios Credito
        # ========================
            # === Prima De Servicios === 
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Prima De Servicios Credito',
                'account_id': acc_config.service_bonus_account_credit.id,
                'debit': 0.0,
                'credit': service_bonus_credit,
            })
            
            # === Cesantias ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Cesantias Credito',
                'account_id': acc_config.severance_account_credit.id,
                'debit': 0.0,
                'credit': severance_credit,
            })
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Intereses Sobre Cesantias Credito',
                'account_id': acc_config.severance_interest_account_credit.id,
                'debit': 0.0,
                'credit': interest_credit,
            })
            
            # === Vacaciones ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Vacaciones Credito',
                'account_id': acc_config.vacation_account_credit.id,
                'debit': 0.0,
                'credit': vacations_credit,
            })
            # ========================
            
            
        # ========================
        # Debito
        # ========================
            # === Sueldos ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Sueldos Debito',
                'account_id': acc_config.wage_account_debit.id,
                'debit': wages_debit,
                'credit': 0.0,
            })
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Comisiones',
                'account_id': acc_config.commission_account_debit.id,
                'debit': commissions,
                'credit': 0.0,
            })
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Incapacidad',
                'account_id': acc_config.arl_incapacity_account_debit.id,
                'debit': incapacity,
                'credit': 0.0,
            })
            
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Auxilio Transporte',
                'account_id': acc_config.transport_allowance_account_debit.id,
                'debit': transport,
                'credit': 0.0,
            })
            
          # === Aportes A Seguridad Social ===

            # === Aportes A Salud ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aporte A Salud Debito',
                'account_id': acc_config.health_account_debit.id,
                'debit': health_debit,
                'credit': 0.0, 
            })
            
            # === Aportes A Pension ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aportes Pensión Debito',
                'account_id': acc_config.pension_account_debit.id,
                'debit': pension_debit,
                'credit': 0.0,
            })
            
            # === Aportes A Arl === 
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aportes A Arl Debit',
                'account_id': acc_config.arl_account_debit.id,
                'debit': arl_debit,
                'credit': 0.0,
            })
                        
          # === Beneficios ===   
          
            # === Prima De Servicios ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Prima De Servicios Debito',
                'account_id': acc_config.service_bonus_account_debit.id,
                'debit': service_bonus_debit,
                'credit': 0.0,
            })
            
            # === Cesantias ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Cesantias Debito',
                'account_id': acc_config.severance_account_debit.id,
                'debit': severance_debit,
                'credit': 0.0,
            })
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Intereses Sobre Cesantias Debito',
                'account_id': acc_config.severance_interest_account_debit.id,
                'debit': interest_debit,
                'credit': 0.0,
            })
            
            # === Vacaciones ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Vacaciones Debito',
                'account_id': acc_config.vacation_account_debit.id,
                'debit': vacations_debit,
                'credit': 0.0,
            })
        # ========================        
        
        
        # ========================
        # Credito 
        # ========================        

            # === Sueldos ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Sueldos Credito',
                'account_id': acc_config.wage_account_credit.id,
                'debit': 0.0,
                'credit': wages_credit,
            })
            
          # === Aportes A Seguridad Social ===
          
            # === Aportes A Salud ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aporte A Salud Credito',
                'account_id': acc_config.health_account_credit.id,
                'debit': 0.0,
                'credit': health_credit, 
            })
            
            # === Aportes A Pension ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aportes Pensión Credito',
                'account_id': acc_config.pension_account_credit.id,
                'debit': 0.0,
                'credit': pension_credit,
            })
            
            # === Aportes A Arl ===
            lines_vals.append({
                'payroll_id': payroll.id,
                'concept_name': 'Aportes A Arl Credit',
                'account_id': acc_config.arl_account_credit.id,
                'debit': 0.0,
                'credit': arl_credit,
            })
        # ========================    
        
            # === Ajuste por redondeo de decimales ===
            total_debit = sum(line['debit'] for line in lines_vals)
            total_credit = sum(line['credit'] for line in lines_vals)
            difference = round(total_debit - total_credit, 2)

            if abs(difference) >= 0.01:
                # Determina si hay más débito o crédito
                adjust_type = 'debit' if difference < 0 else 'credit'
                adjust_value = abs(difference)
                ipdb.set_trace()
                # Añade línea de ajuste al diario para cuadrar el asiento
                lines_vals.append({
                    'payroll_id': payroll.id,
                    'concept_name': 'Ajuste por redondeo',
                    'account_id': acc_config.rounding_credit.id or acc_config.rounding_debit.id,
                    'debit': adjust_value if adjust_type == 'debit' else 0.0,
                    'credit': adjust_value if adjust_type == 'credit' else 0.0,
                })   
    # ========================
        
    # ========================
    # Genera El Asiento Contable En La Base De Datos De Odoo
    # ========================
            # === Trae Los Campos Existentes Dentro De 'account.move.line' ===
            valid_fields = self.env['account.move.line']._fields.keys()
            
            # === Deja Solo Los Campos Necesarios Para La Creacion Del Asiento ===
            clean_lines_vals = []
            for line in lines_vals:
                clean_line = {k: v for k, v in line.items() if k in valid_fields}
                clean_lines_vals.append((0, 0, clean_line))
                
            # === Aplica El Diario Donde Se Almacenara El Asiento Contable ===
            journal = self.env['account.journal'].search([('type', '=', 'general'), ('name', 'ilike', 'Nomina')], limit=1) 
            if not journal:
                raise UserError("Debe crear un diario en facturacion de tipo varios y nombre Nomina.")
            
            # === Ajusta El Movimiento Contable y Le Asigna Un Nombre General, Fecha Y El Diario ===
            move_vals = {
                'ref': payroll.name,
                'date': payroll.date_end,
                'journal_id': journal.id,
                'line_ids': clean_lines_vals,
            }

            ipdb.set_trace()
            # === Llama La Funcion Encargada De Crear Los Asientos Contables ===
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            self.line_vals = lines_vals
            payroll.move_id = move.id
            # Crear todas las líneas
            self.env['hr.payroll.account.line'].create(lines_vals)
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
        ipdb.set_trace()
        lines_vals = []
        for line in employee_lines:
            # Aquí puedes usar la misma lógica contable de tu función global
            # pero restringida solo a ese empleado
            vals = {
                'payroll_id': self.id,
                'employee_id': line.employee_id.id,
                'concept_name': 'Neto a pagar',  # Ejemplo
                'account_id': line.contract_id.account_id.id if line.contract_id.account_id else False,
                'debit': line.net if line.net > 0 else 0.0,
                'credit': 0.0,
                'note': f"Asiento individual de {line.employee_id.name}",
            }
            lines_vals.append(vals)
    
        # Creamos las líneas filtradas
        self.env['hr.payroll.account.line'].create(lines_vals)