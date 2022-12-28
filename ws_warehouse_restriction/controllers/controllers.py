# -*- coding: utf-8 -*-
# from odoo import http


# class WsWarehouseRestriction(http.Controller):
#     @http.route('/ws_warehouse_restriction/ws_warehouse_restriction', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ws_warehouse_restriction/ws_warehouse_restriction/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ws_warehouse_restriction.listing', {
#             'root': '/ws_warehouse_restriction/ws_warehouse_restriction',
#             'objects': http.request.env['ws_warehouse_restriction.ws_warehouse_restriction'].search([]),
#         })

#     @http.route('/ws_warehouse_restriction/ws_warehouse_restriction/objects/<model("ws_warehouse_restriction.ws_warehouse_restriction"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ws_warehouse_restriction.object', {
#             'object': obj
#         })
