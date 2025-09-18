from odoo import models, api
import logging
import ipdb

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("product_id", "move_id.partner_id", "move_id.fiscal_position_id", "price_unit", "quantity")
    def _onchange_product_taxes_with_minimum_base(self):
        move = self.move_id
        if move.move_type not in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            return

        partner = move.partner_id
        base = (self.price_unit or 0.0) * (self.quantity or 0.0)

        # 1) Tomar impuestos definidos en el producto (sin filtrar todavía)
        product_taxes = self.product_id.taxes_id

        # 2) Aplicar fiscal position (mapear impuestos)
        #    map_tax devuelve el set de impuestos que efectivamente se aplicarán
        fpos = move.fiscal_position_id or (partner.property_account_position_id if partner else None)
        if fpos:
            taxes_mapped = fpos.map_tax(product_taxes)
        else:
            taxes_mapped = product_taxes

        # 3) FILTRAR POR BASE MÍNIMA sobre los impuestos mapeados
        taxes_to_apply = taxes_mapped.filtered(
            lambda t: not getattr(t, "minimum_base_amount", 0.0) or base >= (t.minimum_base_amount or 0.0)
        )

        # Debug (temporal si quieres ver qué pasa en logs)
        _logger.info(
            "onchange taxes: move=%s product=%s base=%s mapped=%s filtered=%s",
            move.name or move.id,
            getattr(self.product_id, "name", False),
            base,
            taxes_mapped.mapped("name"),
            taxes_to_apply.mapped("name"),
        )
        # 4) Asignar impuestos finales a la línea
        self.tax_ids = taxes_to_apply

# onchange tax_base_amount de self.move_id
# base_minima > subtotal
# 
# rteIVA
