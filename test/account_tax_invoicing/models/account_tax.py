from odoo import models, fields, api
import ipdb

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    amount_type = fields.Selection(selection_add=[('base', 'Porcentaje sobre monto base mínimo')], ondelete={'base': 'set default'})
    minimum_base_amount = fields.Float(string="Monto base mínimo", help="Si el monto base es menor a este valor, no se aplica el impuesto.")
    over_iva = fields.Boolean(string="Aplicar sobre IVA", default=False, help="Si está marcado, el impuesto se aplicará sobre el monto con IVA incluido.")
    
    
    @api.model
    def _compute_amount(self, base_amount, price_unit, quantity, product=None, partner=None):
        """ Sobrescribimos el cálculo del impuesto.
        """
        self.ensure_one()

        if self.over_iva:
            # Solo aplicar si la base supera el mínimo
            if base_amount >= self.minimum_base_amount:
                # Calculamos IVA manualmente (19% del subtotal)
                iva_amount = base_amount * 0.19
                # Retención del 15% sobre ese IVA
                return iva_amount * self.amount / 100.0
            else:
                return 0.0

        # Si no es ReteIVA, se comporta normal
        return super(AccountTax, self)._compute_amount(
            base_amount, price_unit, quantity, product, partner
        )