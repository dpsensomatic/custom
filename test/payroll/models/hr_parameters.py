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
    arl_fee = fields.Selection([
        ('i','I 0.522%'),
        ('ii','II 1.044%'),
        ('iii','III 2.436%'),
        ('iv','IV 4.350%'),
        ('v','V 6.960%'),
        ],string='Tarifa ARL', default='i', required=True)

    
    # Restricción para que no se repita el año
    _sql_constraints = [
        ("year_unique", "unique(year)", "Ya existe un registro de parámetros para este año."),
    ]
    #=========================
    
    
    #=========================
    # Método para obtener los parámetros vigentes en una fecha dada
    #=========================
    @api.model
    def get_parameters_for_date(self, date):
        """Devuelve parámetros laborales vigentes en la fecha"""
        # Pasa el string de fecha a un objeto date y obtiene el año
        year = date.year if hasattr(date, "year") else fields.Date.from_string(date).year
        # Compara la fecha obtenida con el campo year de los registros
        record = self.search([("year", "=", year)], limit=1)
        
        # Asigna el valor numérico correspondiente a la tarifa de ARL
        arl_fee = record.arl_fee
        if arl_fee == 'i':
            arl_fee_value = 0.522
        elif arl_fee == 'ii':
            arl_fee_value = 1.044
        elif arl_fee == 'iii':
            arl_fee_value = 2.436
        elif arl_fee == 'iv':
            arl_fee_value = 4.350
        elif arl_fee == 'v':
            arl_fee_value = 6.960
        
        # Si no encuentra un registro para ese año, devuelve valores por defecto (0.0)
        if not record:
            return {
                "minimum_wage": 0.0,
                "transport_allowance": 0.0,
                "uvt_value": 0.0,
                "company_eps_percentage": 0.0,
                "employee_eps_percentage": 0.0,
                "company_pension_percentage": 0.0,
                "employee_pension_percentage": 0.0,
                "arl_fee": 0.0,                
            }
        # Si encuentra el registro, devuelve los valores de los campos
        return {
            "minimum_wage": record.minimum_wage,
            "transport_allowance": record.transport_allowance,
            "uvt_value": record.uvt_value,
            "company_eps_percentage": record.company_eps_percentage,
            "employee_eps_percentage": record.employee_eps_percentage,
            "company_pension_percentage": record.company_pension_percentage,
            "employee_pension_percentage": record.employee_pension_percentage,
            "arl_fee": arl_fee_value,
        }