# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrRestDay(models.Model):
    _name = 'hr.rest.day'
    _description='HR Rest Day'
    
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date')
    
    
    def action_post_rest_day(self):
        pass
    
    
    
    
    
    
    
   