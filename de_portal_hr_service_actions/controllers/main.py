# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from markupsafe import Markup

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from odoo.http import request
from odoo.tools.translate import _
from odoo.osv.expression import OR, AND
import base64
from odoo.tools import safe_eval

from odoo.addons.de_portal_hr_service.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):
    def _model_record_get_page_view_values(self, service_id, model_id, record_id, access_token, **kwargs):
        values = super(CustomerPortal, self)._model_record_get_page_view_values(service_id, model_id, record_id, access_token, **kwargs)
        #raise UserError(_(values))
        values.update({
            'portal_hr_service_record_actions_template': self.portal_hr_service_record_actions_template(service_id,record_id),
        })
        return values
    
    def portal_hr_service_record_actions_template(self,service_id,record_id):
        template = ''
        
        service_sudo = request.env['hr.service'].search([('id','=',service_id.id)],limit=1)

        
        if service_sudo.hr_service_action_ids:
            template += '<div class="row bg-secondary mb16">'
            for action in service_sudo.hr_service_action_ids:
                # find editable record option
                # domain to display action buttons
                if action.action_domain and action.display_mode in ('form','all'):
                    domain = safe_eval.safe_eval(action.action_domain)
                    #template += '<h1>' + str(record_id.filtered_domain(domain)) + '</h1>'
                    if record_id.filtered_domain(domain):
                        template += "<t class='col-lg-1 mb8 mt8'>"
                        template +=  "<a href='/my/model/record/action/" + str(service_sudo.id) + "/" + str(service_sudo.header_model_id.id) + "/" + str(record_id.id) + "/" + str(action.id) + "' class='btn btn-primary pull-left' >" + str(action.name) + "</a>"
                        template += "</t>"
            template += "</div>"
        return template
    
        
    
    @http.route(['/my/model/record/action/<int:service_id>/<int:model_id>/<int:record_id>/<int:action_id>'
                ], type='http', auth="user", website=True)        
    def portal_actions_success(self, service_id=False, model_id=False, record_id=False, action_id=False, **kw):
        
        service_sudo = request.env['hr.service'].search([('id','=',service_id)],limit=1)
        action_sudo = request.env['hr.service.actions'].search([('id','=',action_id)],limit=1)
        model_sudo = request.env['ir.model']
        
        if service_sudo.header_model_id.id == model_id:
            model_sudo = service_sudo.header_model_id
            record_sudo = request.env[service_sudo.header_model_id.model].search([('id', '=', record_id)], limit=1).sudo()
        elif service_sudo.line_model_id.id == model_id:
            record_sudo = request.env[service_sudo.line_model_id.model].search([('id', '=', record_id)], limit=1).sudo()
            model_sudo = service_sudo.line_model_id
            
        service_sudo.sudo().exec_server_actions(model_sudo, record_sudo, action_sudo)
        #action_server = action_sudo.action_server_id
        #if action_server:
        #    ctx = {
        #            'active_model': model_sudo.model,
        #            'active_id': record_sudo.id,
        #    }
        #    action_server.sudo().with_context(**ctx).run()
                
        values = {
            'service_id': service_sudo,
            'model_id': model_id,
            'record_id': record_sudo,
            'action_id': action_sudo,
        }
        return request.render("de_portal_hr_service_actions.portal_actions_success", values)
