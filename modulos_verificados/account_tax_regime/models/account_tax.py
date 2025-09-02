from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    minimum_base_amount = fields.Monetary(
        string="Base del impuesto", 
        currency_field='currency_id'
    )
    
    is_withholding = fields.Boolean(
        string="Es retención",
        help="Marcar para impuestos de retención (RteFte, RteIVA, ICA, etc.)."
    )
    
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        _logger.info("[DEBUG] Entró en compute_all de AccountTax")
        _logger.info(f"[DEBUG] Parámetros: price_unit={price_unit}, quantity={quantity}, product={product}, partner={partner}")

        # Llamamos el compute_all original para obtener los impuestos calculados
        res = super().compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include)

        _logger.info(f"[DEBUG] Resultado inicial de compute_all (antes del filtro): {res}")

        for tax in self:
            _logger.info(f"[DEBUG] Revisando impuesto '{tax.name}' con umbral {tax.minimum_base_amount}")

            if tax.minimum_base_amount and res['total_excluded'] < tax.minimum_base_amount:
                _logger.info(f"[DEBUG] No aplica impuesto '{tax.name}'. Base {res['total_excluded']} < umbral {tax.minimum_base_amount}")
                res['taxes'] = [t for t in res['taxes'] if t['id'] != tax.id]
                res['total_included'] = res['total_excluded']  # Ajustamos el total incluido
            else:
                _logger.info(f"[DEBUG] Sí aplica impuesto '{tax.name}'. Base {res['total_excluded']} >= umbral {tax.minimum_base_amount}")

        _logger.info(f"[DEBUG] Resultado final de compute_all (después del filtro): {res}")
        return res
