# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HRPolicyConfiguration(models.Model):
    _name = 'hr.policy.configuration'
    _description = 'HR Policy Configuration'    
    
    name = fields.Char(string='Name', required=True)
    is_active = fields.Boolean(string='Active')
    grace_period = fields.Float(string='Day Grace Time', required=True)
    number_of_late = fields.Float(string='Number of Late', required=True)
    leave_ded = fields.Float(string='Leave Deduction', required=True)
    shift_start_time = fields.Float(string='Shift Start Time', required=True)
    shift_end_time = fields.Float(string='Shift End Time', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    attendance_line_ids = fields.One2many('policy.day.attendance', 'policy_id', string='Day Attendance')
    break_line_ids = fields.One2many('policy.day.break', 'policy_id' , string='Break Lines')
    
    
    def action_allocate_config(self):
        executable_run = self.env['hr.policy.configuration'].search([('is_active','=',True)])
        for ext in executable_run:
            employees = self.env['hr.employee'].search([('company_id','=',ext.company_id.id)])
            for emp in employees:
                pass
            
    
    
class PolicyDayAttendance(models.Model):
    _name = 'policy.day.attendance'
    _description = 'Policy Day Attendance'  
    
    
    type = fields.Selection([
        ('1', 'Full'),
        ('12', 'Half Day'),
        ('13', 'One Third'),        
        ('14', 'One Forth'),
        ], string="Type", default="1", required=True)
    hours = fields.Float(string='Hours', required=True) 
    policy_id = fields.Many2one('hr.policy.configuration', string='Policy')
    
    
    
class PolicyDayBreak(models.Model):
    _name = 'policy.day.break'
    _description = 'Policy Day Break' 
    
    
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),        
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
        ], string="Day Of Week", default="0", required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    policy_id = fields.Many2one('hr.policy.configuration', string='Policy')
    
    
    
    
    
    
        
    