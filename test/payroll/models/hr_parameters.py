from odoo import models, fields, api
import ipdb

class HrParameters(models.Model):
    _name= 'hr.parameters'
    _description= 'Sirve para almacenar todos los parametros que van cambiando con el tiempo'
    
    year = fields.Integer(string="Año", required=True, index=True)
    minimum_wage = fields.Float(string="Salario Mínimo", required=True)
    transport_allowance = fields.Float(string="Auxilio Transporte")
    uvt_value = fields.Float(string="Valor UVT")
    health_ceiling = fields.Float(string="Tope Salud")
    pension_ceiling = fields.Float(string="Tope Pensión")
    
    _sql_constraints = [
        ("year_unique", "unique(year)", "Ya existe un registro de parámetros para este año."),
    ]
    
    
    @api.model
    def get_parameters_for_date(self, date):
        """Devuelve parámetros laborales vigentes en la fecha"""
        year = date.year if hasattr(date, "year") else fields.Date.from_string(date).year
        record = self.search([("year", "=", year)], limit=1)
        if not record:
            return {
                "minimum_wage": 0.0,
                "transport_allowance": 0.0,
                "uvt_value": 0.0,
                "health_ceiling": 0.0,
                "pension_ceiling": 0.0,
            }
        return {
            "minimum_wage": record.minimum_wage,
            "transport_allowance": record.transport_allowance,
            "uvt_value": record.uvt_value,
            "health_ceiling": record.health_ceiling,
            "pension_ceiling": record.pension_ceiling,
        }