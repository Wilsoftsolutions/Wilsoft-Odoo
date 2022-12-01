# -*- coding: utf-8 -*-
# from odoo import http


# class WsHrPayrollEntries(http.Controller):
#     @http.route('/ws_hr_payroll_entries/ws_hr_payroll_entries', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ws_hr_payroll_entries/ws_hr_payroll_entries/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ws_hr_payroll_entries.listing', {
#             'root': '/ws_hr_payroll_entries/ws_hr_payroll_entries',
#             'objects': http.request.env['ws_hr_payroll_entries.ws_hr_payroll_entries'].search([]),
#         })

#     @http.route('/ws_hr_payroll_entries/ws_hr_payroll_entries/objects/<model("ws_hr_payroll_entries.ws_hr_payroll_entries"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ws_hr_payroll_entries.object', {
#             'object': obj
#         })
