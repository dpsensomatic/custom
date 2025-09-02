# -*- coding: utf-8 -*-
# from odoo import http


# class Nomina(http.Controller):
#     @http.route('/nomina/nomina', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nomina/nomina/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('nomina.listing', {
#             'root': '/nomina/nomina',
#             'objects': http.request.env['nomina.nomina'].search([]),
#         })

#     @http.route('/nomina/nomina/objects/<model("nomina.nomina"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nomina.object', {
#             'object': obj
#         })

