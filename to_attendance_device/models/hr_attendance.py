from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter

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
            ('normal', 'Normal'),
            ('late', 'late'),
        ], string='Status',
        default='normal')
    
    
    
        
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            policy = self.env['hr.policy.configuration'].search([('company_id' ,'=', attendance.employee_id.company_id.id),('is_active','=',True)], limit=1)
            policy_day = self.env['policy.day.attendance'].search([('policy_id' ,'=', policy.id),('hours','>=',attendance.worked_hours)], order='hours DESC', limit=1)
            att_count = 1
            if policy_day.type=='1':
                att_count = 1
            elif policy_day.type=='12':  
                att_count = 0.75
            elif policy_day.type=='13':
                att_count = 0.5
            elif policy_day.type=='14':
                att_count = 0.25    
            if str(policy.grace_period) <= str(attendance.check_in.strftime('%H.%M')):
                attendance.update({'attendance_status': 'late', 'company_id': attendance.employee_id.company_id.id,'att_count': att_count})
                
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
    
    
    
    

