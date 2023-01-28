# -*- coding: utf-8 -*-
import time
from odoo import api, models, _ , fields 
from dateutil.parser import parse
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from odoo import exceptions
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


# #  portal Report


class PortalAttendanceReport(models.AbstractModel):
    _name = 'report.ws_hr_attendance.attendance_report_portal'
    _description = 'Hr Attendance Report'

    
    
    
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env['attendance.report.wizard'].browse(self.env.context.get('active_id'))
        employees_attendance = []
        portal_employee = []
        portal_employee = docs.employee_ids.ids
        if not docs.employee_ids:
            portal_employee.append(data['employee'])       
        for employee11 in portal_employee:
            work_day_line = [] 
            employee = self.env['hr.employee'].sudo().search([('id','=', employee11)], limit=1)            
            date_from = docs.start_date
            date_to = docs.end_date
            req_date_from = docs.start_date
            req_date_to = docs.end_date            
            if not docs.employee_ids:
                date_from = datetime.strptime(str(data['start_date']), "%Y-%m-%d")
                date_to = datetime.strptime(str(data['end_date']), "%Y-%m-%d")
                req_date_from = data['start_date']
                req_date_to = data['end_date']
            attendances = []
            remarks = 'Absent'
            holiday = '0'
            rest_day = '0'
            absent = '1'
            delta_days = (date_to - date_from).days + 1
            start_date = date_from
            tot_hours = 0
            rest_day = 'N'
            attendance_day_count = 0
            rest_day_count = 0
            absent_day_count = 0
            leave_day_count = 0
            number_absent_count_over = 0
            for dayline in range(delta_days):
                holiday = '0'
                remarks = 'Absent'
                absent = '1'
                rest_day = 'N'
                
                    
                current_shift = self.env['resource.calendar'].sudo().search([('company_id','=',employee.company_id.id)], limit=1)
                if employee.resource_calendar_id: 
                    current_shift = employee.resource_calendar_id 
                 
                is_rest_day = 0
                attendance_present = self.env['resource.calendar.attendance'].sudo().search([('dayofweek','=',start_date.weekday()),('calendar_id','=',current_shift.id)], limit=1)
#                 raise UserError(str(attendance_present.dayofweek))
                if not attendance_present:
                    is_rest_day = 1                              
                if is_rest_day==1:
                    holiday = '1'
                    rest_day = 'Y'
                    absent = '0'
                    rest_day_count += 1
                    remarks = 'Rest Day'
                for gazetted_day in current_shift.global_leave_ids:
                    gazetted_date_from = gazetted_day.date_from +relativedelta(hours=+5)
                    gazetted_date_to = gazetted_day.date_to +relativedelta(hours=+5)
                    if str(start_date.strftime('%y-%m-%d')) >= str(gazetted_date_from.strftime('%y-%m-%d')) and str(start_date.strftime('%y-%m-%d')) <= str(gazetted_date_to.strftime('%y-%m-%d')): 
                        holiday = '1'
                        rest_day = 'Y'
                        absent = '0'
                        rest_day_count += 1
                        remarks = str(gazetted_day.name)
                        if is_rest_day==1:
                            rest_day_count -=1
                working_hours = 0
                exist_attendances=self.env['hr.attendance'].sudo().search([('employee_id','=',employee.id),('att_date','=',start_date)], order='check_in asc')
                leaves = self.env['hr.leave'].sudo().search([('employee_id','=',employee.id),('request_date_from','<=', start_date),('request_date_to','>=', start_date),('state','in',('confirm','validate'))])
                check_in_time = ''
                check_out_time = ''
                leave_number_of_days = 0
                leave_status = ''
                for leave_day in leaves:
                    if leave_day.state=='validate':
                        leave_status = 'validate'    
                    elif leave_day.state=='confirm':
                        leave_status = 'confirm'  
                    leave_number_of_days += leave_day.number_of_days                          
                rectification = self.env['hr.attendance.rectify'].sudo().search([('employee_id','=',employee.id),('check_in','<=', start_date),('check_out','>=', start_date),('state','in',('submitted','approved'))], limit=1)
                rest_day='Normal' 
                check_in_time = ''
                check_out_time = '' 
                inner_count_fisr=0
                for attendee in exist_attendances:
                    working_hours += attendee.worked_hours
                    inner_count_fisr+=1  
                    if attendee.check_in:
                        if inner_count_fisr==1:
                            check_in_time = attendee.check_in + relativedelta(hours=+5)
                            if attendee.attendance_status=='late':
                                number_absent_count_over += 1  
                                rest_day='Late'  
                    if attendee.check_out: 
                        check_out_time = attendee.check_out + relativedelta(hours=+5)
                                        
                    
                      
                    
                if   (working_hours >= (current_shift.hours_per_day-0.16)):
                    remarks = 'Attendance Present'
                    attendance_day_count += 1
                    absent = '0'
                    if holiday == '1':
                        rest_day_count -= 1   
                elif (working_hours < (current_shift.hours_per_day-0.16)) and (working_hours > (((current_shift.hours_per_day)/4)*3)):
                    attendance_day_count += 0.75
                    remarks = 'One Third Present'          
                elif (working_hours < (current_shift.hours_per_day)) and (working_hours >((current_shift.hours_per_day)/2)):
                    attendance_day_count += 0.5
                    remarks = 'Half Present'    
                    if holiday != '1':
                        if rectification.state=='approved':
                            remarks = 'Rectification (Approved)'
                            absent = '0'
                            attendance_day_count += 0.5
                        elif leave_status=='validate' and leave_number_of_days >= 0.5:
                            remarks = 'Leave (Approved)[0.5]'
                            leave_day_count += 0.5
                            absent = '0'
                            
                        elif leave_status=='validate' and leave_number_of_days == 0.25:
                            remarks = 'Half Present (Leave[Approved] (0.25))'
                            if working_hours < (((current_shift.hours_per_day-1.5)/4)*3):
                                absent = '1'
                                leave_day_count += 0.25
                                absent_day_count += 0.25
                            else:
                                remarks = 'Attendance Present (Leave[Approved] (0.25))' 
                                attendance_day_count += 0.25
                                absent = '0'
                        elif rectification.state=='submitted':
                            absent = '1'
                            remarks = 'Half Present (Rectification [To Approve])'
                            absent_day_count = 0.5
                        elif not rectification and leave_status=='confirm':
                            if leave_number_of_days >= 0.5:
                                absent = '1'
                                remarks = 'Half Present (Leave [To Approve] (0.5))'
                                absent_day_count += 0.5
                            elif leave_number_of_days == 0.25:
                                absent = '1'
                                remarks = 'Half Present (Leave [To Approve] (0.25))'
                                absent_day_count += 0.5
                            else:
                                absent = '1'
                                absent_day_count += 1 
                        else:
                             absent = '1'
                             absent_day_count += 0.5
                    else:
                        if holiday == '1': 
                            attendance_day_count -= 0.5   
                else:
                    if holiday != '1':
                        if rectification.state=='approved':
                            remarks = 'Rectification (Approved)'
                            attendance_day_count += 1
                            absent = '0'
                        elif leave_status=='validate' and leave_number_of_days >= 1:
                            remarks = 'Leave (Approved)'
                            leave_day_count += 1
                            absent = '0'
                        elif rectification.state=='submitted':
                            absent = '1'
                            remarks = 'Rectification (To Approve)'
                            absent_day_count += 1
                        elif leave_status=='confirm':
                            if leave_number_of_days >= 1:
                                absent = '1'
                                remarks = 'Leave (To Approve)'
                                absent_day_count += 1
                            elif leave_number_of_days >= 0.5:
                                absent = '1'
                                remarks = 'Half Leave (To Approve) (0.5)'
                                absent_day_count += 1 
                            elif leave_number_of_days >= 0.25:
                                absent = '1'
                                remarks = 'Short Leave (To Approve) (0.25)'
                                absent_day_count += 1
                            else:
                                absent = '1'
                                absent_day_count += 1
                        elif leave_status=='validate':
                            if leave_number_of_days >= 0.5:
                                absent = '1'
                                remarks = 'Half Leave (Approved) (0.5)'
                                leave_day_count += 0.5
                                absent_day_count += 0.5
                            elif leave_number_of_days >= 0.25:
                                absent = '1'
                                remarks = 'Short Leave (Approved) (0.25)'
                                leave_day_count += 0.25
                                absent_day_count += 0.75
                            else:
                                absent = '1'
                                absent_day_count += 1     
                        else:
                            absent = '1'
                            absent_day_count += 1
                            
                present = 'A' 
                if  absent!='1':  
                    present = 'P'
                if  working_hours >= 24:
                    remarks = 'Working Hours are wrong' 
                    present = 'E'
                    absent = '1'            
                attendances.append({
                    'date': start_date.strftime('%d/%b/%Y'),
                    'day':  start_date.strftime('%A'),
                    'check_in': check_in_time.strftime('%d/%b/%Y %H:%M:%S') if check_in_time else '',
                    'check_out':  check_out_time.strftime('%d/%b/%Y %H:%M:%S') if check_out_time else '',
                    'hours': working_hours,
                    'present': present,
                    'shift': current_shift.name,
                    'holiday': holiday,
                    'absent': absent,
                    'rest_day': rest_day,
                    'remarks': remarks,
                }) 
                start_date = (start_date + timedelta(1))  
            number_absent_count_over = number_absent_count_over - 2
            if number_absent_count_over < 0:
                number_absent_count_over=0 
            number_absent_count_over = number_absent_count_over*0.25        
            employees_attendance.append({
                'name': employee.name,
                'employee_no': '',
                'attendances': attendances,
                'attendance_day_count': attendance_day_count - number_absent_count_over,
                'rest_day_count': rest_day_count,
                'absent_day_count': float(absent_day_count) + float(number_absent_count_over),
                'leave_day_count': leave_day_count,
            }) 
        
        return {
                'employees_attendance': employees_attendance,
                'date_from': datetime.strptime(str(date_from.strftime('%Y-%m-%d')), "%Y-%m-%d").strftime('%Y-%m-%d'),
                'date_to': datetime.strptime(str(date_to.strftime('%Y-%m-%d')), "%Y-%m-%d").strftime('%Y-%m-%d'),
               }
        
        
        



