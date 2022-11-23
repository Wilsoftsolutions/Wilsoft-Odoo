# -*- coding: utf-8 -*-
# from odoo import http


# class DeHrPayrollPolicy(http.Controller):
#     @http.route('/de_hr_payroll_policy/de_hr_payroll_policy', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_hr_payroll_policy/de_hr_payroll_policy/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_hr_payroll_policy.listing', {
#             'root': '/de_hr_payroll_policy/de_hr_payroll_policy',
#             'objects': http.request.env['de_hr_payroll_policy.de_hr_payroll_policy'].search([]),
#         })

#     @http.route('/de_hr_payroll_policy/de_hr_payroll_policy/objects/<model("de_hr_payroll_policy.de_hr_payroll_policy"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_hr_payroll_policy.object', {
#             'object': obj
#         })
