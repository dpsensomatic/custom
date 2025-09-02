# -*- coding: utf-8 -*-
# from odoo import http


# class PruebaSubirRepositorio(http.Controller):
#     @http.route('/prueba_subir_repositorio/prueba_subir_repositorio', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/prueba_subir_repositorio/prueba_subir_repositorio/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('prueba_subir_repositorio.listing', {
#             'root': '/prueba_subir_repositorio/prueba_subir_repositorio',
#             'objects': http.request.env['prueba_subir_repositorio.prueba_subir_repositorio'].search([]),
#         })

#     @http.route('/prueba_subir_repositorio/prueba_subir_repositorio/objects/<model("prueba_subir_repositorio.prueba_subir_repositorio"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('prueba_subir_repositorio.object', {
#             'object': obj
#         })

