from odoo import models, fields, api
import ipdb
import logging
_logger = logging.getLogger(__name__)

# ==========================
# Modelo Con Ajustes Totales
# ==========================
class AccountMoveLine (models.Model):
    # === Descripcion Del Modelo ===
    _inherit = 'account.move.line'
    
    # ==========================
    # Funcionamiento Del Modelo
    # ==========================
    @api.onchange('product_id', 'price_unit', 'quantity', 'tax_ids', 'move_id')
    def _onchange_product_taxes(self):
        for line in self:
            move = line.move_id
            if not move:
                continue

            # ==========================
            # Subtotal global REAL
            # ==========================
            invoice_lines = move.invoice_line_ids if move.invoice_line_ids else move.line_ids
            total_subtotal = sum((l.price_unit or 0)*(l.quantity or 0) for l in move.invoice_line_ids)

            # ==========================
            # Impuestos con base mínima
            # ==========================
            base_taxes = self.env['account.tax'].search([('minimum_base_amount', '>', 0)])

            apply_taxes = base_taxes.filtered(
                lambda t: total_subtotal >= (t.minimum_base_amount or 0.0)
            )

            # ==========================
            # Impuestos del producto
            # ==========================
            product_taxes = line.product_id.taxes_id.filtered(
                lambda t: t.company_id == move.company_id
            )

            # ==========================
            # Asignar impuestos finales
            # ==========================
            ipdb.set_trace()
            line.tax_ids = product_taxes | apply_taxes
        _logger.info("Entró al onchange de impuestos para la línea %s", self.id)
    # ==========================
# ==========================