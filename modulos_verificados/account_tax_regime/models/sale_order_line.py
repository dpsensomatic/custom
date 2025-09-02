from odoo import models,api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_id", "order_id.partner_id", "order_id.fiscal_position_id")
    def _onchange_product_id_regime_taxes(self):
        order = self.order_id
        partner = order.partner_shipping_id or order.partner_id
        regime = partner.x_tax_regime_id
        if not regime:
            return
        add_taxes = regime.tax_ids.filtered(
            lambda t: t.company_id == order.company_id and t.type_tax_use in ("sale", "none")
        )
        fpos = order.fiscal_position_id or partner.property_account_position_id
        if fpos:
            add_taxes = fpos.map_tax(add_taxes)
        # Unir sin duplicar
        self.tax_id = (self.tax_id | add_taxes)
    