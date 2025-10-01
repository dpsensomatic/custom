# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    apply_on_invoice_total = fields.Boolean(
        string="Aplicar sobre subtotal de la factura",
        help="Si está marcado, este impuesto se calculará sobre el subtotal de la factura "
             "y no por cada línea de producto.",
        default=False,
    )

    @api.model
    def _prepare_tax_lines(self, base_lines_values, company, tax_lines=None):
        """Extiende el core añadiendo impuestos que aplican sobre el subtotal de la factura.

        Se asegura de ser tolerante: si no hay datos en base_lines_values hace fallback con las líneas del move.
        Añade dicts a results['tax_lines_to_add'] con la forma que usa _sync_tax_lines.
        """
        results = super()._prepare_tax_lines(base_lines_values, company, tax_lines=tax_lines)

        # obtener move (si base_lines_values viene del core)
        move = None
        if base_lines_values:
            first = base_lines_values[0].get('record')
            if first:
                move = first.move_id

        if not move:
            # fallback: si no tenemos move, no hacemos nada
            _logger.debug("account_tax_regime: no move en base_lines_values, saliendo de _prepare_tax_lines")
            return results

        if not move.is_invoice(include_receipts=True):
            return results

        # Calculamos la base: preferimos lo que ya entregó core en base_lines_values
        base_total = 0.0
        if base_lines_values:
            for bl in base_lines_values:
                tax_details = bl.get('tax_details') or {}
                base_total += tax_details.get('total_excluded', 0.0)

        # Si core no proveyó tax_details, fallback a sumar subtotales de líneas de producto
        if not base_total:
            base_total = sum(
                (l.price_subtotal or 0.0)
                for l in move.line_ids.filtered(lambda r: r.display_type == 'product')
            )

        # Buscar impuestos marcados como apply_on_invoice_total y aplicables a la compañía
        invoice_taxes = self.env['account.tax'].search([
            ('apply_on_invoice_total', '=', True),
            ('active', '=', True),
        ]).filtered(lambda t: (not t.company_id) or (t.company_id == move.company_id))

        if not invoice_taxes:
            _logger.debug("account_tax_regime: no invoice_taxes found for move %s", move.id)
            return results

        # nos aseguramos de que exista la lista
        results.setdefault('tax_lines_to_add', [])

        # recolectar tax ids ya presentes en el move (evitar duplicados)
        existing_tax_ids = set(
            l.tax_line_id.id for l in move.line_ids.filtered(lambda x: x.tax_line_id)
        )

        for tax in invoice_taxes:
            if tax.id in existing_tax_ids:
                _logger.debug("account_tax_regime: tax %s ya presente en move %s, salto", tax.id, move.id)
                continue

            # MVP: solo percent por ahora
            if tax.amount_type != 'percent':
                _logger.debug("account_tax_regime: tax %s tipo %s no soportado (solo percent)", tax.id, tax.amount_type)
                continue

            # coger la repartition line con cuenta
            repart = tax.repartition_line_ids.filtered(lambda r: r.account_id)[:1]
            if not repart:
                _logger.warning("account_tax_regime: tax %s no tiene repartition con account_id, se omite", tax.id)
                continue

            amount = (base_total or 0.0) * (tax.amount or 0.0) / 100.0
            balance = -amount if move.is_sale_document(include_receipts=True) else amount

            tax_line_vals = {
                'name': tax.name or '',
                'tax_line_id': tax.id,
                'tax_repartition_line_id': repart.id,
                'account_id': repart.account_id.id,
                'balance': balance,
                'amount_currency': 0.0,
                'partner_id': move.partner_id.id or False,
                'currency_id': move.currency_id.id if move.currency_id and move.currency_id != move.company_id.currency_id else False,
            }

            _logger.info("account_tax_regime: añadiento tax_line para move %s tax %s amount %.2f", move.id, tax.id, amount)
            results['tax_lines_to_add'].append(tax_line_vals)

        return results
