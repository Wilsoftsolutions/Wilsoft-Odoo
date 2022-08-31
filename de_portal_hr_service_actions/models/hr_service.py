# -*- coding: utf-8 -*-

import base64

import json

from odoo import api, fields, models, tools, _
from odoo.modules.module import get_module_resource
from random import randint
from odoo.exceptions import UserError
import csv
import xlrd
from odoo.tools import ustr
import logging

_logger = logging.getLogger(__name__)

from odoo.exceptions import Warning
from odoo import models, fields, exceptions, api, _
import io
import tempfile
import binascii
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

from odoo.tools import safe_eval


class HRService(models.Model):
    _inherit = 'hr.service'
    
    READONLY_STATES = {
        'validate': [('readonly', True)],
        'publish': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    
    hr_service_action_ids = fields.One2many('hr.service.actions', 'hr_service_id', string='Service Actions', copy=True, auto_join=True, states=READONLY_STATES,)
    hr_service_approver_ids = fields.One2many('hr.service.approvers', 'hr_service_id', string='Service Approver', copy=True, auto_join=True, states=READONLY_STATES,)
    

    def exec_server_actions(self, model_id, record_id, action_id):
        action_sudo = self.env['hr.service.actions']
        for service in self:
            action_server = action_id.action_server_id
            if action_server:
                ctx = {
                    'active_model': model_id.model,
                    'active_id': record_id.id,
                }
                action_server.sudo().with_context(**ctx).run()

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    
    def button_test_method(self):
        #safe_eval.safe_eval(self.code)
        records = self
        action_server = self.action_server_id
        #raise UserError(self.header_model_name)
        if action_server:
            for record in records:
                # we process the action if any watched field has been modified
                #if self._check_trigger_fields(record):
                ctx = {
                    'active_model': self.header_model_name,
                    'active_ids': record.ids,
                    'active_id': 1, #record.id,
                    #'domain_post': domain_post,
                }
                #try:
                action_server.sudo().with_context(**ctx).run()
                #except Exception as e:
                    #self._add_postmortem_action(e)
                    #raise UserError(_('exception'))
                #    return False
                        
        
    def button_test_method1(self):
        method_list = []

        # attribute is a string representing the attribute name
        for attribute in dir(HRService):
            # Get the attribute value
            attribute_value = getattr(HRService, attribute)
            # Check that it is callable
            if callable(attribute_value):
                # Filter all dunder (__ prefix) methods
                if attribute.startswith('button_') == True or attribute.startswith('action_') == True:
                    method_list.append(attribute)

        raise UserError(_(method_list))
        #mymethod = 'self.' + self.method + '()'
        #result = self.eval(mymethod)
        
    def action_test_method(self):
        raise UserError(_('the method has been called'))

class HRServiceApprover(models.Model):
    _name = 'hr.service.approvers'
    _description = 'Service Approvers'
    
    
    hr_service_id = fields.Many2one('hr.service', string='HR Service', readonly=True)
    user_type = fields.Selection([
        ('manager', 'Line Manager'),
        ('hod', 'HOD'),
        ('custom', 'Custom'),
    ], string='Type', default='manager', required=True)
    user_id = fields.Many2one('res.users', string='Approver')
    
    
class HRServiceActions(models.Model):
    _name = 'hr.service.actions'
    _description = 'Service Actions'
    _order = 'sequence, id'
    
    
    hr_service_id = fields.Many2one('hr.service', string='HR Service', readonly=True,)
    header_model_id = fields.Many2one('ir.model', related='hr_service_id.header_model_id', string='Model')

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    method = fields.Char(string="Method")
    action_server_id = fields.Many2one("ir.actions.server", string="Action", ondelete="cascade")
    action_domain = fields.Char(string='Action Domain', help="If present, this condition must be satisfied before executing the action rule.")
    
    code = fields.Text(string='Python Code', groups='base.group_system',
                       help="Write Python code that the action will execute. Some variables are "
                            "available for use; help about python expression is given in the help tab.")
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set an email will be sent to the customer when the task or issue reaches this step.")
    
    display_mode = fields.Selection([
        ('form', 'Form View'),
        ('list', 'List View'),
        ('all', 'All'),
    ], string='Display On', default='form', required=True)

    
