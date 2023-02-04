# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta



class HRPolicyConfiguration(models.Model):
    _name = 'hr.policy.configuration'
    _description = 'HR Policy Configuration'    
    
    name = fields.Char(string='Name', required=True)
    is_active = fields.Boolean(string='Active')
    grace_period = fields.Float(string='Day Grace Time', required=True)
    max_grace_period = fields.Float(string='Grace Period End')
    number_of_late = fields.Float(string='Number of Late', required=True)
    number_of_short = fields.Float(string='Number of Short', required=True)
    
    leave_ded = fields.Float(string='Leave Deduction', required=True)
    shift_start_time = fields.Float(string='Shift Start Time', required=True)
    shift_end_time = fields.Float(string='Shift End Time', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    attendance_line_ids = fields.One2many('policy.day.attendance', 'policy_id', string='Day Attendance')
    attendance_in_line_ids = fields.One2many('policy.day.attendance.in', 'policy_id', string='Day Attendance In')
    attendance_out_line_ids = fields.One2many('policy.day.attendance.out', 'policy_id', string='Day Attendance Out')
    break_line_ids = fields.One2many('policy.day.break', 'policy_id' , string='Break Lines')
    
    
    def action_allocate_config(self):
        executable_run = self.env['hr.policy.configuration'].search([('is_active','=',True)])
        for ext in executable_run:
            employees = self.env['hr.employee'].search([('company_id','=',ext.company_id.id)])
            for emp in employees:
                settle_date = fields.date.today() - timedelta(2)
                exist_att = self.env['hr.attendance'].search([('employee_id','=',emp.id),('att_date','=',settle_date),('worked_hours','>',0),('is_validated','=',False)], limit=1)
                if exist_att:
                    checking_date = exist_att.check_in+relativedelta(hours=+5)
                    
                    if checking_date.strftime('%H:%M').replace(':','.') > str(ext.grace_period):
                        exist_att.update({
                            'is_validated': True
                        })
                        leave_type = self.env['hr.leave.type'].search([('unpaid_leave','=',True)], limit=1)
                        leave_types = self.env['hr.leave.type'].search([('leave_priority','!=',0)], order='leave_priority ASC')
                        for type in leave_types:
                            total_allocations = 0
                            total_leaves = 0 
                            allocation = self.env['hr.leave.allocation'].search([('employee_id','=',emp.id),('state','=','validate'),('holiday_status_id','=',type.id)])
                            leaves = self.env['hr.leave'].search([('employee_id','=',emp.id),('state','=','validate'),('holiday_status_id','=',type.id)])
                            for alloc in allocation:
                                total_allocations += alloc.number_of_days
                            for leav in leaves:
                                total_leaves += leav.number_of_days 
                            remaining_alloc =  total_allocations - total_leaves   
                            if   total_allocations >  total_leaves and remaining_alloc > ext.leave_ded: 
                                leave_type = type
                                break;
                        line_vals = {
                            'employee_id': emp.id,
                            'number_of_days': ext.leave_ded,
                            'request_date_from': exist_att.check_in,
                            'request_date_to': exist_att.check_in,
                            'holiday_status_id': leave_type.id,
                            'name': 'Leave Deduction Due To Late Arrival',
                        }
                        leave = self.env['hr.leave'].create(line_vals)
                        leave.update({
                            'number_of_days': ext.leave_ded,
                        })
                        leave.action_approve()
                        if leave.state!='validate':
                            leave.action_validate()
            
    
 
class PolicyDayAttendance(models.Model):
    _name = 'policy.day.attendance.in'
    _description = 'Policy Day Attendance IN'  
    
    
    type = fields.Selection([
        ('1', 'Full'),
        ('12', 'Half Day'),
        ('13', 'One Third'),        
        ('14', 'One Forth'),
        ('15', 'Absent'),
        ], string="Type", default="1", required=True)
    date_from = fields.Float(string='Time From',  required=True) 
    date_to = fields.Float(string='Time To',  required=True) 
    policy_id = fields.Many2one('hr.policy.configuration', string='Policy') 
    
    
class PolicyDayAttendance(models.Model):
    _name = 'policy.day.attendance.out'
    _description = 'Policy Day Attendance OUT'  
    
    
    type = fields.Selection([
        ('1', 'Full'),
        ('12', 'Half Day'),
        ('13', 'One Third'),        
        ('14', 'One Forth'),
        ('15', 'Absent'),
        ], string="Type", default="1", required=True)
    date_from = fields.Float(string='Time From',  required=True) 
    date_to = fields.Float(string='Time To',  required=True) 
    policy_id = fields.Many2one('hr.policy.configuration', string='Policy')     
    
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
    
    
    
    
class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    leave_priority = fields.Integer(string='Attendance Deduction (Priority)')
    unpaid_leave = fields.Boolean(string='Unpaid Leave')
    is_deduct = fields.Boolean(string='Is Deduct')
    
    
        
    
