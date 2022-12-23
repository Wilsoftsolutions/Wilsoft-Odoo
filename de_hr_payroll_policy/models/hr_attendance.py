# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    is_validated = fields.Boolean(string='Is Validate')
    
    