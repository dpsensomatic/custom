from odoo import models, fields, api
import ipdb

class HrParameters(models.Model):
    # ==========================
    # Definición del modelo
    # ==========================
    _name= 'hr.parameters'
    _description= 'Sirve para almacenar todos los parametros que van cambiando con el tiempo'
    # ==========================
    
    #=========================
    # Campos del modelo
    #=========================
    year = fields.Integer(string="Año", required=True, index=True)
    minimum_wage = fields.Float(string="Salario Mínimo", required=True)
    transport_allowance = fields.Float(string="Auxilio Transporte")
    uvt_value = fields.Float(string="Valor UVT")
    company_eps_percentage = fields.Float(string="EPS Empresa")
    employee_eps_percentage = fields.Float(string="EPS Trabajador")
    company_pension_percentage = fields.Float(string="Pensión Empresa")
    employee_pension_percentage = fields.Float(string="Pensión Trabajador")
    

    
    # === Restricción para que no se repita el año ===
    _sql_constraints = [
        ("year_unique", "unique(year)", "Ya existe un registro de parámetros para este año."),
    ]
    #=========================