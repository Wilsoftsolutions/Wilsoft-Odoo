# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'
    
    fiscal_year = fields.Char(related='holiday_status_id.fiscal_year')