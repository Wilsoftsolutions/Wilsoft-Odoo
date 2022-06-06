# -*- coding: utf-8 -*-
# from odoo import http


# class SalePurchaseTax(http.Controller):
#     @http.route('/sale_purchase_tax/sale_purchase_tax/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_purchase_tax/sale_purchase_tax/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_purchase_tax.listing', {
#             'root': '/sale_purchase_tax/sale_purchase_tax',
#             'objects': http.request.env['sale_purchase_tax.sale_purchase_tax'].search([]),
#         })

#     @http.route('/sale_purchase_tax/sale_purchase_tax/objects/<model("sale_purchase_tax.sale_purchase_tax"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_purchase_tax.object', {
#             'object': obj
#         })
