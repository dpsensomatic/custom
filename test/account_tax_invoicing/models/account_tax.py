# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = "account.tax"

    # currency para el field Monetary
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    minimum_base_amount = fields.Monetary(
        string="Base mínima",
        currency_field='currency_id',
        help="Si la base (por línea) es menor a este valor, el impuesto no se aplica."
    )

    over_iva = fields.Boolean(
        string="Aplicar sobre IVA",
        default=False,
        help="Si está marcado, el impuesto se calculará sobre el IVA (en vez de sobre la base directamente)."
    )

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None,
                    is_refund=False, handle_price_include=True):
        """
        Heredamos compute_all para:
         - Filtrar impuestos que no alcanzan la base mínima (minimum_base_amount)
         - Si over_iva == True: recalcular el monto del impuesto como (IVA_line_amount * tax.rate)
        Nota: se asume versión "simple" de IVA (si no encuentras IVA real aún, usamos 19%).
        """
        # Llamamos a la implementación original
        res = super().compute_all(price_unit, currency, quantity, product, partner,
                                  is_refund=is_refund, handle_price_include=handle_price_include)

        try:
            # base de la línea sin impuestos
            base = res.get('total_excluded', 0.0)

            # recalculemos taxes list (es una lista de dicts)
            taxes_list = res.get('taxes', [])

            # Para cada impuesto del recordset self, aplicamos nuestras reglas
            for tax in self:
                # Buscar entradas de este impuesto en taxes_list
                tax_entries = [t for t in taxes_list if t.get('id') == tax.id]
                if not tax_entries:
                    # este impuesto no estaba presente en el cálculo original (p. ej. price_include handling),
                    # nada que hacer
                    continue

                # Si hay base mínima configurada y la base es menor -> eliminar impuesto
                min_base = tax.minimum_base_amount or 0.0
                if min_base and base < min_base:
                    _logger.debug("Tax '%s' no aplica: base %s < min %s", tax.name, base, min_base)
                    # eliminar las entradas de este impuesto
                    taxes_list = [t for t in taxes_list if t.get('id') != tax.id]
                    # actualizar res (total_included)
                    total_tax = sum(t.get('amount', 0.0) for t in taxes_list)
                    res['taxes'] = taxes_list
                    res['total_included'] = res.get('total_excluded', 0.0) + total_tax
                    continue

                # Si over_iva está marcado, recalculamos el amount del impuesto en función del IVA
                if tax.over_iva:
                    # Versión simple (rápida): calcular IVA como base * 0.19
                    # (más adelante haremos la versión que detecta el IVA real)
                    iva_amount = base * 0.19
                    # tasa del impuesto (p. ej. 15 -> 0.15)
                    pct = (tax.amount or 0.0) / 100.0
                    new_amount = iva_amount * pct

                    _logger.debug("Tax '%s' over_iva: base=%s iva=%s pct=%s -> new_amount=%s",
                                  tax.name, base, iva_amount, pct, new_amount)

                    # sustituimos el/los amount(s) de las entradas correspondientes
                    for entry in taxes_list:
                        if entry.get('id') == tax.id:
                            entry['amount'] = new_amount

                    # recalcular total_included
                    total_tax = sum(t.get('amount', 0.0) for t in taxes_list)
                    res['taxes'] = taxes_list
                    res['total_included'] = res.get('total_excluded', 0.0) + total_tax
                else:
                    # no over_iva y no min_base => dejamos lo que el core calculó para ese impuesto
                    # (o bien si min_base==0 y base >= min_base, no hacemos nada)
                    pass

            # aseguar res['taxes'] actualizado
            res['taxes'] = taxes_list

        except Exception as e:
            _logger.exception("Error personalizado en AccountTax.compute_all: %s", e)

        # Debug: si quieres activar logging verás el res
        _logger.debug("compute_all (post) -> total_excluded=%s total_included=%s taxes=%s",
                      res.get('total_excluded'), res.get('total_included'), [(t.get('id'), t.get('amount')) for t in res.get('taxes', [])])

        return res
