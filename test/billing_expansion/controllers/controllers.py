# -*- coding: utf-8 -*-
# from odoo import http


# class BillingExpansion(http.Controller):
#     @http.route('/billing_expansion/billing_expansion', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/billing_expansion/billing_expansion/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('billing_expansion.listing', {
#             'root': '/billing_expansion/billing_expansion',
#             'objects': http.request.env['billing_expansion.billing_expansion'].search([]),
#         })

#     @http.route('/billing_expansion/billing_expansion/objects/<model("billing_expansion.billing_expansion"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('billing_expansion.object', {
#             'object': obj
#         })

