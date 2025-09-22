from odoo import models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def apply_taxes_on_iva_draft(self):
        """Calcular retenciones sobre IVA y añadir/actualizar líneas en memoria (draft).
           Usa .new() para no requerir move_id en bd.
        """
        for move in self:
            # obtener taxes marcados para aplicar sobre IVA
            taxes_on_iva = self.env['account.tax'].search([('is_tax_on_vat', '=', True)])
            if not taxes_on_iva:
                # limpiar líneas draft de retención si necesitas (opcional)
                continue

            # subtotal sin IVA
            subtotal_base = sum(move.invoice_line_ids.mapped('price_subtotal'))

            # total IVA: buscar líneas de impuesto ya generadas en draft
            iva_lines = move.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.tax_group_id and 'IVA' in (l.tax_line_id.tax_group_id.name or ''))
            iva_total = sum(iva_lines.mapped('balance'))

            for tax in taxes_on_iva:
                if subtotal_base < (tax.minimum_base_amount or 0.0):
                    # si no aplica, intentar borrar línea temporal si existe
                    existing = move.line_ids.filtered(lambda l: l.tax_line_id == tax)
                    # borrar sólo líneas nuevas en memoria si las encontramos (no persistidas)
                    # Se puede filtrar por new ids; pero simplificamos: si existe y es persisted, lo dejamos
                    continue

                rte_amount = iva_total * (tax.amount or 0.0) / 100.0

                # buscar línea temporal existente (new records included)
                existing = move.line_ids.filtered(lambda l: l.tax_line_id == tax and not l.id)  # new ones have no id
                if existing:
                    # actualizar valores en memoria
                    existing.write({
                        'name': tax.name,
                        'debit': -rte_amount if rte_amount < 0 else 0.0,
                        'credit': rte_amount if rte_amount > 0 else 0.0,
                        'balance': -rte_amount,
                    })
                else:
                    # conseguir cuenta para la línea (invoice_repartition_line_ids)
                    account = tax.invoice_repartition_line_ids.mapped('account_id')[:1]
                    if not account:
                        # si no hay cuenta configurada, salta (o alerta)
                        _logger.warning("Tax %s no tiene account en invoice_repartition_line_ids", tax.name)
                        continue

                    new_line = self.env['account.move.line'].new({
                        'move_id': move.id,
                        'name': tax.name,
                        'tax_line_id': tax.id,
                        'account_id': account.id,
                        'debit': -rte_amount if rte_amount < 0 else 0.0,
                        'credit': rte_amount if rte_amount > 0 else 0.0,
                        'balance': -rte_amount,
                        'partner_id': move.partner_id.id,
                        'company_currency_id': move.company_id.currency_id.id,
                        'company_id': move.company_id.id,
                    })
                    # añadir a las líneas del move en memoria
                    move.line_ids += new_line

    def apply_taxes_on_iva_post(self):
        """Crear/actualizar las líneas persistentes de retención una vez posteada la factura."""
        for move in self:
            taxes_on_iva = self.env['account.tax'].search([('is_tax_on_vat', '=', True)])
            if not taxes_on_iva:
                continue

            subtotal_base = sum(move.invoice_line_ids.mapped('price_subtotal'))
            iva_lines = move.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.tax_group_id and 'IVA' in (l.tax_line_id.tax_group_id.name or ''))
            iva_total = sum(iva_lines.mapped('balance'))

            for tax in taxes_on_iva:
                if subtotal_base < (tax.minimum_base_amount or 0.0):
                    continue

                rte_amount = iva_total * (tax.amount or 0.0) / 100.0

                # buscar línea persistente existente
                existing = move.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id == tax and l.id)
                if existing:
                    existing.sudo().write({
                        'debit': -rte_amount if rte_amount < 0 else 0.0,
                        'credit': rte_amount if rte_amount > 0 else 0.0,
                        'balance': -rte_amount,
                    })
                else:
                    account = tax.invoice_repartition_line_ids.mapped('account_id')[:1]
                    if not account:
                        raise UserError(f"El impuesto {tax.name} no tiene cuenta contable configurada (invoice_repartition_line_ids).")
                    self.env['account.move.line'].sudo().create({
                        'move_id': move.id,
                        'name': tax.name,
                        'tax_line_id': tax.id,
                        'account_id': account.id,
                        'debit': -rte_amount if rte_amount < 0 else 0.0,
                        'credit': rte_amount if rte_amount > 0 else 0.0,
                        'balance': -rte_amount,
                        'partner_id': move.partner_id.id,
                        'company_currency_id': move.company_id.currency_id.id,
                        'company_id': move.company_id.id,
                    })

    def action_post(self):
        """Al postear, primero ejecutar el core y luego crear las líneas de retención persistentes."""
        res = super().action_post()
        # ahora crear/actualizar las retenciones
        self.apply_taxes_on_iva_post()
        return res

    def _prepare_tax_line_vals(self, line, tax, tax_amount, tax_amount_currency, base_amount):
        vals = super()._prepare_tax_line_vals(line, tax, tax_amount, tax_amount_currency, base_amount)
        # Si es retención, ocultarlo del panel de impuestos de la factura
        if tax.is_retention:
            vals['exclude_from_invoice_tab'] = True
        return vals
