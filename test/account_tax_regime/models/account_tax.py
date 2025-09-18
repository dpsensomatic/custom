from odoo import models, fields, api
import logging
import ipdb

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # --- NUEVOS CAMPOS ---
    minimum_base_amount = fields.Monetary(
        string="Base mínima",
        currency_field='company_currency_id',
        help="Si la base imponible es menor a este valor, el impuesto no se aplicará."
    )

    is_withholding = fields.Boolean(
        string="Es retención",
        help="Marcar si este impuesto corresponde a una retención (RteFte, RteIVA, ICA, etc.)."
    )

    # --- CAMPOS RELACIONADOS ---
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    # # --- LÓGICA ---
    # def compute_all(
    #     self,
    #     price_unit,
    #     currency=None,
    #     quantity=1.0,
    #     product=None,
    #     partner=None,
    #     is_refund=False,
    #     handle_price_include=True,
    # ):
    #     """
    #     Sobrescribimos compute_all para que respete la base mínima configurada en el impuesto.
    #     """
    #     # Calculamos normalmente primero
    #     res = super().compute_all(
    #         price_unit, currency, quantity, product, partner, is_refund, handle_price_include
    #     )

    #     base_amount = res.get("total_excluded", 0.0)

    #     # Filtramos los impuestos que no cumplen la base mínima
    #     new_taxes = []
    #     for tax in self:
    #         if tax.minimum_base_amount and base_amount < tax.minimum_base_amount:
    #             _logger.debug(
    #                 "El impuesto %s (id=%s) NO aplica. Base=%.2f < mínimo=%.2f",
    #                 tax.name, tax.id, base_amount, tax.minimum_base_amount,
    #             )
    #             # Lo quitamos (no lo agregamos a new_taxes)
    #             continue
    #         new_taxes.extend([t for t in res["taxes"] if t["id"] == tax.id])

    #     # Reemplazamos la lista de impuestos filtrada
    #     res["taxes"] = new_taxes
    #     # Si eliminamos impuestos, ajustamos el total incluido
    #     res["total_included"] = res["total_excluded"] + sum(
    #         t.get("amount", 0.0) for t in res["taxes"]
    #     )
    #     ipdb.set_trace()
    #     return res
