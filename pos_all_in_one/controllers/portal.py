from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request
from odoo import http


class WeblearnPortal(CustomerPortal):

    def _prepare_portal_values(self, request):
        print(11111111111111111111111111)
        rtn = super(WeblearnPortal, self)._prepare_home_portal_values(request)
        print(11111111111111111111111111)
        rtn['partner_count'] = request.env['res.partner'].search_count([])
        print(11111111111111111111111111)
        return rtn

        @http.route('/my/students', type='http')
        def weblearnStudent(self, **kw):
            return http.request.render('idt_approval_request.listing', {
                'root': '/idt_approval_request/idt_approval_request',
                'objects': http.request.env['idt_approval_request.idt_approval_request'].search([]),
            })