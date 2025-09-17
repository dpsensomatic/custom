# -*- coding: utf-8 -*-
# from odoo import http


# class AccountTaxRegime(http.Controller):
#     @http.route('/account_tax_regime/account_tax_regime', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_tax_regime/account_tax_regime/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_tax_regime.listing', {
#             'root': '/account_tax_regime/account_tax_regime',
#             'objects': http.request.env['account_tax_regime.account_tax_regime'].search([]),
#         })

#     @http.route('/account_tax_regime/account_tax_regime/objects/<model("account_tax_regime.account_tax_regime"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_tax_regime.object', {
#             'object': obj
#         })

