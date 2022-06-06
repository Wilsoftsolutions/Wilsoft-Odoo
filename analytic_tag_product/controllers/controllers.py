# -*- coding: utf-8 -*-
# from odoo import http


# class AnalyticTagProduct(http.Controller):
#     @http.route('/analytic_tag_product/analytic_tag_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_tag_product/analytic_tag_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_tag_product.listing', {
#             'root': '/analytic_tag_product/analytic_tag_product',
#             'objects': http.request.env['analytic_tag_product.analytic_tag_product'].search([]),
#         })

#     @http.route('/analytic_tag_product/analytic_tag_product/objects/<model("analytic_tag_product.analytic_tag_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_tag_product.object', {
#             'object': obj
#         })
