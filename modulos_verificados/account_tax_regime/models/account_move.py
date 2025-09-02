from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    x_misc_tax_total = fields.Monetary(
        string="Impuestos varios",
        compute="_compute_x_misc_tax_total",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("line_ids.tax_line_id", "line_ids.balance", "line_ids.tax_line_id.tax_group_id")
    def _compute_x_misc_tax_total(self):
        codes_for_misc = {"RETFTE", "RTEICA", "RTEIVA", "OTROS"}
        for move in self:
            total = sum(
                line.balance
                for line in move.line_ids.filtered(
                    lambda l: l.tax_line_id and l.tax_line_id.tax_group_id.code in codes_for_misc
                )
            )
            move.x_misc_tax_total = abs(total)

    # -------------------------------
    # RETENCIONES
    # -------------------------------

    def _get_partner_withholdings(self, partner):
        """Devuelve los impuestos de retención que aplican al partner."""
        if not partner:
            return self.env["account.tax"]

        taxes = partner.withholding_tax_ids

        # Si usas los booleanos en el partner, intenta buscar por nombre
        def _find(keyword):
            return self.env["account.tax"].search([
                ("is_withholding", "=", True),
                ("name", "ilike", keyword),
            ], limit=1)

        # OJO: el campo en tu res.partner es apply_rteica_withholding
        if partner.apply_rteica_withholding:
            t = _find("ICA")
            if t:
                taxes |= t
        if partner.apply_rteiva_withholding:
            t = _find("Rete IVA")
            if t:
                taxes |= t
        if partner.apply_rtefte_withholding:
            t = _find("Rete Fuente")
            if t:
                taxes |= t

        # Para ventas: 'sale' o 'none'
        return taxes.filtered(lambda t: t.type_tax_use in ("sale", "none"))

    def _apply_partner_withholdings_to_lines(self):
        """Inserta las retenciones del partner en cada línea de factura."""
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                continue

            partner_taxes = move._get_partner_withholdings(move.partner_id)
            if not partner_taxes:
                continue

            for line in move.invoice_line_ids:
                if line.display_type:
                    continue
                new_taxes = (line.tax_ids | partner_taxes)
                line.tax_ids = [(6, 0, new_taxes.ids)]

    # -------------------------------
    # HOOKS
    # -------------------------------

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        # Recalcula dinámicos primero y luego aplica retenciones
        try:
            self._recompute_dynamic_lines()
        except Exception:
            # En algunas ediciones puede no existir; ignoramos
            pass
        self._apply_partner_withholdings_to_lines()
        return res

    @api.onchange("invoice_line_ids")
    def _onchange_invoice_line_ids(self):
        # NO llames a super: no existe en esta versión
        try:
            self._recompute_dynamic_lines()
        except Exception:
            pass
        self._apply_partner_withholdings_to_lines()
        # onchanges sin return explícito están OK

    def write(self, vals):
        res = super().write(vals)
        for move in self.filtered(lambda m: m.state == "draft"):
            move._apply_partner_withholdings_to_lines()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for move in records:
            if move.state == "draft":
                move._apply_partner_withholdings_to_lines()
        return records
