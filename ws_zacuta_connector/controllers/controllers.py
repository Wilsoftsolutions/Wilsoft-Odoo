# -*- coding: utf-8 -*-
# from odoo import http


# class WsZacutaConnector(http.Controller):
#     @http.route('/ws_zacuta_connector/ws_zacuta_connector', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ws_zacuta_connector/ws_zacuta_connector/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ws_zacuta_connector.listing', {
#             'root': '/ws_zacuta_connector/ws_zacuta_connector',
#             'objects': http.request.env['ws_zacuta_connector.ws_zacuta_connector'].search([]),
#         })

#     @http.route('/ws_zacuta_connector/ws_zacuta_connector/objects/<model("ws_zacuta_connector.ws_zacuta_connector"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ws_zacuta_connector.object', {
#             'object': obj
#         })
