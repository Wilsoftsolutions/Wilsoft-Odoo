# -*- coding: utf-8 -*-
# from odoo import http


# class WsLoanRequest(http.Controller):
#     @http.route('/ws_loan_request/ws_loan_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ws_loan_request/ws_loan_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ws_loan_request.listing', {
#             'root': '/ws_loan_request/ws_loan_request',
#             'objects': http.request.env['ws_loan_request.ws_loan_request'].search([]),
#         })

#     @http.route('/ws_loan_request/ws_loan_request/objects/<model("ws_loan_request.ws_loan_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ws_loan_request.object', {
#             'object': obj
#         })
