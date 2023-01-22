# -*- coding: utf-8 -*-
# from odoo import http


# class WsMaterialRequestReport(http.Controller):
#     @http.route('/ws_material_request_report/ws_material_request_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ws_material_request_report/ws_material_request_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ws_material_request_report.listing', {
#             'root': '/ws_material_request_report/ws_material_request_report',
#             'objects': http.request.env['ws_material_request_report.ws_material_request_report'].search([]),
#         })

#     @http.route('/ws_material_request_report/ws_material_request_report/objects/<model("ws_material_request_report.ws_material_request_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ws_material_request_report.object', {
#             'object': obj
#         })
