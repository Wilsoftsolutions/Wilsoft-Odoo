# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    is_publish = fields.Boolean(string='Publish on Portal')
    fiscal_year = fields.Char(string='Year', required=True)
    category_id = fields.Many2one('category.approval', string='Category', required=True)
