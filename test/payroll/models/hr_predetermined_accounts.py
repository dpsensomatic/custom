from odoo import models, fields, api
import ipdb

# ========================
# Definicion Del Modelo
# ========================
class HrPredeterminedAccounts(models.Model):
    
    # === Descripcion Del Modelo ===
    _name = 'hr.predetermined.accounts'
    _description = 'Cuentas Predeterminadas Para el Modulo De Nomina'
    _rec_name = "company_id"
    
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade"
    )

# === Campos Del Modelo ===

  # === Redondeo De decimales ===
    rounding_debit = fields.Many2one("account.account", string="Cuenta Sueldos Debito")
    rounding_credit = fields.Many2one("account.account", string="Cuenta Sueldos Credito")

  # === Sueldos Nomina ===   
    wage_account_debit = fields.Many2one("account.account", string="Cuenta Sueldos Debito")
    wage_account_credit = fields.Many2one("account.account", string="Cuenta Sueldos Credito")
    
  # === Retenciones ===
    withholding_tax_account_debit = fields.Many2one("account.account", string="Cuenta Retenciones Debito")
    withholding_tax_account_credit = fields.Many2one("account.account", string="Cuenta Retenciones Credito") 
    
  # === Novedades ===
    # === Licencias No Remuneradas ===
    unpaid_days_account_debit = fields.Many2one("account.account", string="Cuenta Días No Pagos Debito")
    unpaid_days_account_credit = fields.Many2one("account.account", string="Cuenta Días No Pagos Credito")
    
    # === EPS Incapacidad ===
    eps_incapacity_account_debit = fields.Many2one("account.account", string="Cuenta Incapacidad EPS Debito")
    eps_incapacity_account_credit = fields.Many2one("account.account", string="Cuenta Incapacidad EPS Credito")
    
    # === ARL Incapacidad ===
    arl_incapacity_account_debit = fields.Many2one("account.account", string="Cuenta Incapacidad ARL Debito")
    arl_incapacity_account_credit = fields.Many2one("account.account", string="Cuenta Incapacidad ARL Credito")
    
    # === Comisiones ===
    commission_account_debit = fields.Many2one("account.account", string="Cuenta Comisiones Debito")
    commission_account_credit = fields.Many2one("account.account", string="Cuenta Comisiones Credito")
    

  # === Auxilios ===
    # === Auxilio De Transporte ===
    transport_allowance_account_debit = fields.Many2one("account.account", string="Cuenta Auxilio Transporte Debito")
    transport_allowance_account_credit = fields.Many2one("account.account", string="Cuenta Auxilio Transporte Credito")
    
    # === Auxilio De Transporte ===
    cellular_allowance_account_debit = fields.Many2one("account.account", string="Cuenta Auxilio Celular Debito")
    cellular_allowance_account_credit = fields.Many2one("account.account", string="Cuenta Auxilio Celular Credito")
    
    
  # === Aportes A Seguridad Social ===
    # === Aportes Eps ===
    health_account_credit = fields.Many2one("account.account", string="Cuenta Salud Credito")
    health_account_debit = fields.Many2one("account.account", string="Cuenta Salud Debito")
    
    # === Aportes Pension ===
    pension_account_credit = fields.Many2one("account.account", string="Cuenta Pension Credito")
    pension_account_debit = fields.Many2one("account.account", string="Cuenta Pension Debito")
    
    # === Aportes Arl ===
    arl_account_credit = fields.Many2one("account.account", string="Cuenta ARL Credito")
    arl_account_debit = fields.Many2one("account.account", string="Cuenta ARL Debito")
    
  #  === Aportes Parafiscales ===
    # === Aportes Caja Compensacion ===
    compensation_fund_credit = fields.Many2one("account.account", string="Cuenta Caja Credito")
    compensation_fund_debit = fields.Many2one("account.account", string="Cuenta Caja Debito")

    # === Aportes Sena ===
    sena_credit = fields.Many2one("account.account", string="Cuenta Sena Credito")
    sena_debit = fields.Many2one("account.account", string="Cuenta Sena Debito")
    
    # === Aportes ICBF ===
    icbf_credit = fields.Many2one("account.account", string="Cuenta ICBF Credito")
    icbf_debit = fields.Many2one("account.account", string="Cuenta ICBF Debito")
    
  # === Bonificaciones ===
    # === Cesantias ===  
    severance_account_debit = fields.Many2one("account.account", string="Cuenta Cesantías Debito")
    severance_account_credit = fields.Many2one("account.account", string="Cuenta Cesantías Credito")
    
    severance_interest_account_debit = fields.Many2one("account.account", string="Cuenta Intereses Cesantías Debito")
    severance_interest_account_credit = fields.Many2one("account.account", string="Cuenta Intereses Cesantías Credito")
    
    
    # === Prima De Servicios ===
    service_bonus_account_debit = fields.Many2one("account.account", string="Cuenta Prima de Servicios Debito")
    service_bonus_account_credit = fields.Many2one("account.account", string="Cuenta Prima de Servicios Credito")
    
    
    # === Vacaciones ===
    vacation_account_debit = fields.Many2one("account.account", string="Cuenta Vacaciones Debito")
    vacation_account_credit = fields.Many2one("account.account", string="Cuenta Vacaciones Credito")
    
    
    _sql_constraints = [
        ('unique_company', 'unique(company_id)', 'Solo puede existir una configuración por compañía.'),
    ]
    
     
    # === Método práctico para obtener cuentas ===
    @api.model
    def _get_account(self, field_name):
        """Devuelve la cuenta configurada para un campo determinado."""
        rec = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not rec:
            return False
        return getattr(rec, field_name, False)