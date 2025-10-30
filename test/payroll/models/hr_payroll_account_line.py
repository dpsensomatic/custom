from odoo import models, fields, api

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
    debit = fields.Monetary( currency_field="currency_id")
    credit = fields.Monetary( currency_field="currency_id")
    debit_float = fields.Float(string="Débito", compute="_compute_float_values", store=False)
    credit_float = fields.Float(string="Crédito", compute="_compute_float_values", store=False)
    
    
    # === Campos Char ===
    concept_name = fields.Char(string="Concepto")
    
    
    # === Campos Many ===
    account_id = fields.Many2one("account.account", string="Cuenta contable", required=True)
    currency_id = fields.Many2one("res.currency", related="payroll_id.currency_id", store=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado")
    
# ========================

    @api.depends('debit', 'credit')
    def _compute_float_values(self):
        for rec in self:
            rec.debit_float = rec.debit
            rec.credit_float = rec.credit