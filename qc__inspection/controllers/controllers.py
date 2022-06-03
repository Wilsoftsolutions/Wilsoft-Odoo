# -*- coding: utf-8 -*-
# from odoo import http


# class QcInspection(http.Controller):
#     @http.route('/qc__inspection/qc__inspection', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/qc__inspection/qc__inspection/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('qc__inspection.listing', {
#             'root': '/qc__inspection/qc__inspection',
#             'objects': http.request.env['qc__inspection.qc__inspection'].search([]),
#         })

#     @http.route('/qc__inspection/qc__inspection/objects/<model("qc__inspection.qc__inspection"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('qc__inspection.object', {
#             'object': obj
#         })
