# -*- coding: utf-8 -*-
# from odoo import http


# class Invoicing(http.Controller):
#     @http.route('/invoicing/invoicing', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/invoicing/invoicing/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('invoicing.listing', {
#             'root': '/invoicing/invoicing',
#             'objects': http.request.env['invoicing.invoicing'].search([]),
#         })

#     @http.route('/invoicing/invoicing/objects/<model("invoicing.invoicing"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('invoicing.object', {
#             'object': obj
#         })

