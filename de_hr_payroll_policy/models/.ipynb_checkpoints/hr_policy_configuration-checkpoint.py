# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HRPolicyConfiguration(models.Model):
    _name = 'hr.policy.configuration'
    _description = 'HR Policy Configuration'    
    
    grace_period = fields.Float(string='Day Grace Time')
    number_of_late = fields.Float(string='Number of Late')
    leave_ded = fields.Float(string='Leave Deduction')
    shift_start_time = fields.Float(string='Shift Start Time')
    shift_end_time = fields.Float(string='Shift End Time')
    
    
class PolicyDayAttendance(models.Model):
    _name = 'policy.day.attendance'
    _description = 'Policy Day Attendance'  
    
    
    type = fields.Selection([
        ('1', 'Full'),
        ('12', 'Half Day'),
        ('13', 'One Third'),        
        ('14', 'One Forth'),
        ], string="Type", default="1")
    hours = fields.Float(string='Hours')   
    
    
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
        ], string="Day Of Week", default="0")
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    
    
    
    
    
    
        
    