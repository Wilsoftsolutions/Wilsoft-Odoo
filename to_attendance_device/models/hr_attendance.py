from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from dateutil.relativedelta import relativedelta

from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero



class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    checkin_device_id = fields.Many2one('attendance.device', string='Checkin Device', readonly=True, index=True,
                                        help='The device with which user took check in action')
    checkout_device_id = fields.Many2one('attendance.device', string='Checkout Device', readonly=True, index=True,
                                         help='The device with which user took check out action')
    activity_id = fields.Many2one('attendance.activity', string='Attendance Activity',
                                  help='This field is to group attendance into multiple Activity (e.g. Overtime, Normal Working, etc)')
    company_id = fields.Many2one('res.company', string='Company')
    att_count = fields.Float(string='Day')
    attendance_status = fields.Selection(selection=[
            ('1', 'Full'),
            ('12', 'Half Day'),
            ('13', 'One Third'),        
            ('14', 'One Forth'),
            ('15', 'Absent'),
            ('16', 'Late'),
        ], string='Status',
        default='1' )
    
    
    
        
from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from dateutil.relativedelta import relativedelta

from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero



class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    checkin_device_id = fields.Many2one('attendance.device', string='Checkin Device', readonly=True, index=True,
                                        help='The device with which user took check in action')
    checkout_device_id = fields.Many2one('attendance.device', string='Checkout Device', readonly=True, index=True,
                                         help='The device with which user took check out action')
    activity_id = fields.Many2one('attendance.activity', string='Attendance Activity',
                                  help='This field is to group attendance into multiple Activity (e.g. Overtime, Normal Working, etc)')
    company_id = fields.Many2one('res.company', string='Company')
    att_count = fields.Float(string='Day')
    attendance_status = fields.Selection(selection=[
            ('1', 'Full'),
            ('12', 'Half Day'),
            ('13', 'One Third'),        
            ('14', 'One Forth'),
            ('15', 'Absent'),
            ('16', 'Late'),
        ], string='Status',
        default='1')
    
    
    
        
    @api.constrains('check_in', 'check_out')
    def _check_attendance_Status(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            attendance.update({'attendance_status': '1', 'company_id': attendance.employee_id.company_id.id,'att_count': 0})
            working_hrs=0 
            record_count=0
            test_check_out=0
            policy=attendance.employee_id.policy_id
            exist_policy = self.env['hr.policy.configuration'].search([('date_from','!=',False),('date_to','!=',False),('date_from','<=',attendance.att_date),('date_to','>=',attendance.att_date)], limit=1)
            
            if exist_policy:
                policy= exist_policy   
            exist_record=self.env['hr.attendance'].search([('employee_id','=',attendance.employee_id.id),('att_date','=',attendance.att_date)], order='check_in asc')
            for ext_l in exist_record:
                record_count+=1
                working_hrs += ext_l.worked_hours
            
            if  attendance.worked_hours==0.0:
                att_count = 0
            test_check_in =  attendance.check_in + relativedelta(hours=+5)
            exist_record=self.env['hr.attendance'].search([('employee_id','=',attendance.employee_id.id),('att_date','=',attendance.att_date)], order='check_in asc')
            
            test_check_in =  attendance.check_in + relativedelta(hours=+5)
            for ext_att in exist_record:
                test_check_in =  ext_att.check_in + relativedelta(hours=+5)
                test_check_out = ext_att.check_in + relativedelta(hours=+5)
                break
            for ext_att in exist_record:
                if ext_att.check_out:
                    test_check_out =  ext_att.check_out + relativedelta(hours=+5)     
            policy_dayin = self.env['policy.day.attendance.in'].search([
            ('policy_id' ,'=', policy.id),
            ('date_from','<=',float(test_check_in.strftime('%H.%M'))),
            ('date_to','>=',float(test_check_in.strftime('%H.%M')))], order='date_from DESC', limit=1)
            
            policy_dayout = self.env['policy.day.attendance.out'].search([
            ('policy_id' ,'=', policy.id),
            ('date_from','<=',float(test_check_out.strftime('%H.%M'))),
            ('date_to','>=',float(test_check_out.strftime('%H.%M')))], order='date_from DESC', limit=1)
                    
            att_count = 1
            in_att_count = 1
            out_att_count = 1
            
            status = '15'
            if policy_dayin.type=='1':
                in_att_count = 1
                status = '1'
            elif policy_dayin.type=='12':  
                in_att_count = 0.5
                status = '12'
            elif policy_dayin.type=='13':
                in_att_count = 0.75
                status = '13'
            elif policy_dayin.type=='14':
                in_att_count = 0.25
                status = '14'
            elif policy_dayin.type=='16':
                in_att_count = 1
                status = '16'     
            else:
                in_att_count = 0 
                status = '15'
            ######### 
            out_status = '15'
            if policy_dayout.type=='1':
                out_att_count = 1
                out_status = '1'
            elif policy_dayout.type=='12':  
                out_att_count = 0.5
                out_status = '12'
            elif policy_dayout.type=='13':
                out_att_count = 0.75
                out_status = '13'
            elif policy_dayout.type=='14':
                out_att_count = 0.25
                out_status = '14' 
            elif policy_dayout.type=='16':
                out_att_count = 1
                out_status = '16'    
            else:
                out_att_count = 0 
             
            
            if in_att_count < out_att_count:
                att_count=in_att_count               
            elif in_att_count > out_att_count:
                att_count=out_att_count 
                status = out_status 
            else:
                att_count=in_att_count 
                
            if float(policy.grace_period) <= float(test_check_in.strftime('%H.%M')) and float(policy.max_grace_period) > float(test_check_in.strftime('%H.%M')):
                inn_record_count=0 
                for upd_att in exist_record:
                    inn_record_count+=1
                    if inn_record_count==1:
                        upd_att.update({'attendance_status': '16', 'company_id': attendance.employee_id.company_id.id,'att_count': att_count})
            else:
                inn_record_count=0
                for upd_att in exist_record:
                    inn_record_count+=1
                    if inn_record_count==1:
                        upd_att.update({'attendance_status': status, 'company_id': attendance.employee_id.company_id.id,'att_count': att_count})
                        
                        
    
        
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out."""
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))
                    
                    

                    

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                pass

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    pass
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    pass
    
    
    
    


        
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out."""
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))
                    
                    

                    

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                pass

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    pass
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    pass
    
    
    
    

