# -*- coding: utf-8 -*-
# from odoo import http


# class DeliveryReport(http.Controller):
#     @http.route('/delivery_report/delivery_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/delivery_report/delivery_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('delivery_report.listing', {
#             'root': '/delivery_report/delivery_report',
#             'objects': http.request.env['delivery_report.delivery_report'].search([]),
#         })

#     @http.route('/delivery_report/delivery_report/objects/<model("delivery_report.delivery_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('delivery_report.object', {
#             'object': obj
#         })
