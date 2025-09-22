from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('product_id', 'price_unit', 'quantity', 'move_id')
    def _onchange_product_taxes_with_minimum_base(self):
        """Asignar taxes al cambiar producto/qty/price. Filtra por minimum_base_amount
           y aplica fiscal position. Luego actualiza líneas de retención en draft.
        """
        for line in self:
            move = line.move_id
            if not move or move.move_type not in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
                continue

            partner = move.partner_id
            base = (line.price_unit or 0.0) * (line.quantity or 0.0)

            # 1) impuestos definidos en el producto
            product_taxes = line.product_id.taxes_id

            # 2) aplicar fiscal position (map_tax)
            fpos = move.fiscal_position_id or (partner.property_account_position_id if partner else None)
            taxes_mapped = fpos.map_tax(product_taxes) if fpos else product_taxes

            # 3) filtrar por base mínima (campo minimum_base_amount)
            taxes_to_apply = taxes_mapped.filtered(
                lambda t: not getattr(t, 'minimum_base_amount', 0.0) or base >= (t.minimum_base_amount or 0.0)
            )

            # 4) asignar
            line.tax_ids = taxes_to_apply

        # Al terminar de ajustar líneas, forzamos actualización de las líneas de impuestos en draft
        if self and self[0].move_id:
            # función que maneja retenciones en draft (usa .new() internamente)
            self[0].move_id.apply_taxes_on_iva_draft()
