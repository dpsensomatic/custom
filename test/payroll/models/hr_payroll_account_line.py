from odoo import models, fields

# ========================
# Definicion Del Modelo
# ========================
class HrPayrollAccountLine(models.Model):
    
    # === Descripcion Del Modelo ===
    _name = "hr.payroll.account.line"
    _description = "Línea contable de nómina"

  # === Campos Del Modelo ===
  
    # === Campo many conectado con hr_payroll ===
    payroll_id = fields.Many2one(
        "hr.payroll",
        string="Nómina",
        ondelete="cascade",
    )
    
    
    # === Campos Monetary === 
    debit = fields.Monetary(string="Débito", currency_field="currency_id", default=0.0)
    credit = fields.Monetary(string="Crédito", currency_field="currency_id", default=0.0)
    
    
    # === Campos Char ===
    note = fields.Char(string="Nota")
    concept_name = fields.Char(string="Concepto")
    
    
    # === Campos Many ===
    account_id = fields.Many2one("account.account", string="Cuenta contable", required=True)
    currency_id = fields.Many2one("res.currency", related="payroll_id.currency_id", store=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado")
    
# ========================
