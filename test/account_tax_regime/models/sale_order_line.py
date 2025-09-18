from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_id", "order_id.partner_id", "order_id.fiscal_position_id", "price_unit", "product_uom_qty")
    def _onchange_product_id_minimum_base_taxes(self):
        order = self.order_id
        partner = order.partner_shipping_id or order.partner_id
        base = self.price_unit * self.product_uom_qty

        # === 1. impuestos del producto (con validación de base mínima) ===
        product_taxes = self.product_id.taxes_id.filtered(
            lambda t: not t.minimum_base_amount or base >= t.minimum_base_amount
        )

        # === 2. aplicar fiscal position (si existe) ===
        fpos = order.fiscal_position_id or partner.property_account_position_id
        if fpos:
            product_taxes = fpos.map_tax(product_taxes)

        # === 3. asignar ===
        self.tax_id = product_taxes
