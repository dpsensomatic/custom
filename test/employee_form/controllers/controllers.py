# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeeForm(http.Controller):
#     @http.route('/employee_form/employee_form', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_form/employee_form/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_form.listing', {
#             'root': '/employee_form/employee_form',
#             'objects': http.request.env['employee_form.employee_form'].search([]),
#         })

#     @http.route('/employee_form/employee_form/objects/<model("employee_form.employee_form"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_form.object', {
#             'object': obj
#         })

