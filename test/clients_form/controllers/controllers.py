# -*- coding: utf-8 -*-
# from odoo import http


# class ClientsForm(http.Controller):
#     @http.route('/clients_form/clients_form', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/clients_form/clients_form/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('clients_form.listing', {
#             'root': '/clients_form/clients_form',
#             'objects': http.request.env['clients_form.clients_form'].search([]),
#         })

#     @http.route('/clients_form/clients_form/objects/<model("clients_form.clients_form"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('clients_form.object', {
#             'object': obj
#         })

