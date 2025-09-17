# -*- coding: utf-8 -*-
# from odoo import http


# class AccountTaxInvoicing(http.Controller):
#     @http.route('/account_tax_invoicing/account_tax_invoicing', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_tax_invoicing/account_tax_invoicing/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_tax_invoicing.listing', {
#             'root': '/account_tax_invoicing/account_tax_invoicing',
#             'objects': http.request.env['account_tax_invoicing.account_tax_invoicing'].search([]),
#         })

#     @http.route('/account_tax_invoicing/account_tax_invoicing/objects/<model("account_tax_invoicing.account_tax_invoicing"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_tax_invoicing.object', {
#             'object': obj
#         })

