from odoo import models, api, fields

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    global_discount = fields.Float(string="Descuento Global (%)", default=0.0)

    @api.onchange('global_discount', 'invoice_line_ids')
    def _apply_global_discount(self):
        for move in self:
            discount = move.amount_untaxed * (move.global_discount / 100)
            # Crea o actualiza una línea de descuento negativo
            discount_line = move.invoice_line_ids.filtered(lambda l: l.name == 'Descuento global')
            if discount_line:
                discount_line.price_unit = -discount
            else:
                move.update({
                    'invoice_line_ids': [(0, 0, {
                        'name': 'Descuento global',
                        'price_unit': -discount,
                        'quantity': 1,
                        'account_id': move.journal_id.default_account_id.id,
                        'tax_ids': [(6, 0, move.invoice_line_ids.mapped('tax_ids').ids)],
                    })]
                })


    def apply_global_taxes_draft(self):
        """Añade impuestos marcados como globales en facturas en estado borrador (no persiste)."""
        for move in self:
            if not move.is_invoice(include_receipts=True):
                continue

            global_taxes = self.env['account.tax'].search([
                ('apply_on_invoice_total', '=', True),
                ('company_id', '=', move.company_id.id),
            ])
            if not global_taxes:
                continue

            base = sum(line.price_subtotal for line in move.invoice_line_ids)

            for tax in global_taxes:
                amount = base * (tax.amount / 100.0)
                move.line_ids += self.env['account.move.line'].new({
                    'move_id': move.id,
                    'name': tax.name,
                    'account_id': tax.invoice_repartition_line_ids[0].account_id.id,
                    'debit': amount if amount > 0 else 0.0,
                    'credit': -amount if amount < 0 else 0.0,
                    'tax_line_id': tax.id,
                })

    @api.onchange('invoice_line_ids')
    def _onchange_lines_global_taxes(self):
        """Cuando cambian las líneas de factura recalculamos impuestos y sumamos los globales."""
        self._recompute_tax_lines()   # Odoo hace lo suyo
        self.apply_global_taxes_draft()  # metemos los globales

    def action_post(self):
        """Al validar factura, persistimos los impuestos globales en el apunte contable."""
        res = super().action_post()
        for move in self:
            if not move.is_invoice(include_receipts=True):
                continue

            global_taxes = self.env['account.tax'].search([
                ('apply_on_invoice_total', '=', True),
                ('company_id', '=', move.company_id.id),
            ])
            if not global_taxes:
                continue

            base = sum(line.price_subtotal for line in move.invoice_line_ids)

            for tax in global_taxes:
                amount = base * (tax.amount / 100.0)
                self.env['account.move.line'].create({
                    'move_id': move.id,
                    'name': tax.name,
                    'account_id': tax.invoice_repartition_line_ids[0].account_id.id,
                    'debit': amount if amount > 0 else 0.0,
                    'credit': -amount if amount < 0 else 0.0,
                    'tax_line_id': tax.id,
                })
        return res