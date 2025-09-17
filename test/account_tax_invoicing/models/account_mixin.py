# -*- coding: utf-8 -*-
from odoo import models, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("product_id", "move_id.partner_id", "move_id.fiscal_position_id", "price_unit", "quantity")
    def _onchange_product_taxes_with_regime_and_minimum_base(self):
        move = self.move_id
        if move.move_type not in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            return

        partner = move.partner_id
        base = (self.price_unit or 0.0) * (self.quantity or 0.0)

        # 1) impuestos del producto. Filtramos por base mínima si existe
        product_taxes = self.product_id.taxes_id.filtered(
            lambda t: not t.minimum_base_amount or base >= t.minimum_base_amount
        )

        # 2) impuestos del régimen del partner (si tienes tax_regime)
        regime_taxes = self.env["account.tax"]
        regime = partner.x_tax_regime_id if partner else None
        if regime:
            scope = "sale" if move.is_sale_document(include_receipts=True) else "purchase"
            regime_taxes = regime.tax_ids.filtered(
                lambda t: t.company_id == move.company_id
                and t.type_tax_use in (scope, "none")
                and (not t.minimum_base_amount or base >= t.minimum_base_amount)
            )

        # 3) combinación y mapeo por fpos
        all_taxes = product_taxes | regime_taxes

        fpos = move.fiscal_position_id or (partner.property_account_position_id if partner else None)
        if fpos:
            all_taxes = fpos.map_tax(all_taxes)

        # 4) asignar impuestos a la línea
        self.tax_ids = all_taxes
