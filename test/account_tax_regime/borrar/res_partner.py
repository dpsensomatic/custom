from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_tax_regime_id = fields.Many2many(
        "x.tax.regime", string="Impuesto de regimen")

    property_account_receivable_id = fields.Many2one(
        "account.account",
        string='Cuenta por cobrar',
        domain="[('account_type', '=', 'asset_receivable')]"
    )

    property_account_payable_id = fields.Many2one(
        "account.account",
        string='Cuentas por pagar',
        domain='[("account_type", "=", "liability_payable")]'
    )

    apply_rteica_withholding = fields.Boolean(string="Aplicar Rte ICA")
    apply_rteiva_withholding = fields.Boolean(string="Aplicar Rte IVA")
    apply_rtefte_withholding = fields.Boolean(string="Aplicar Rte Fuente")


    # Config general (recomendado): lista de impuestos de retención a aplicar a este partner
    withholding_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="res_partner_withholding_tax_rel",   # nombre único de la tabla rel
        column1="partner_id",                         # columna que apunta a res.partner
        column2="tax_id",                             # columna que apunta a account.tax
        string="Impuestos de Retención",
        domain="[('is_withholding','=',True)]",
        help="Impuestos de retención que se aplicarán automáticamente a las facturas."
    )

