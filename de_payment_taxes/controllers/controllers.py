# -*- coding: utf-8 -*-
# from odoo import http


# class DePaymentTaxes(http.Controller):
#     @http.route('/de_payment_taxes/de_payment_taxes', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_payment_taxes/de_payment_taxes/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_payment_taxes.listing', {
#             'root': '/de_payment_taxes/de_payment_taxes',
#             'objects': http.request.env['de_payment_taxes.de_payment_taxes'].search([]),
#         })

#     @http.route('/de_payment_taxes/de_payment_taxes/objects/<model("de_payment_taxes.de_payment_taxes"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_payment_taxes.object', {
#             'object': obj
#         })
