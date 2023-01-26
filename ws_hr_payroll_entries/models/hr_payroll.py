# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    
    def _get_available_contracts_domain(self):
        return [('contract_ids.state', 'in', ('open', 'close')), ('company_id', '=', self.env.company.id)]

    def _get_employees(self):
        active_employee_ids = self.env.context.get('active_employee_ids', False)
        if active_employee_ids:
            employees_slip = self.env['hr.employee'].browse(active_employee_ids)
            employees_end = employees_slip.search([('stop_salary','=',False)])
            return employees_end
        # YTI check dates too
        final_emp_list = self.env['hr.employee'].search(self._get_available_contracts_domain())
        final_emp = final_emp_list.search([('stop_salary','=',False)])
        return final_emp


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    
    def compute_sheet(self):
        for payslip in self:
            data=[]
            
                
            """Attendance Count"""
            attendances = self.env['hr.attendance'].search([('employee_id','=',payslip.employee_id.id),('att_date','>=',payslip.date_from),('att_date','<=',payslip.date_to)])
            attendance_day=0
            for att in attendances:
                attendance_day += att.att_count
            att_end = self.env['hr.work.entry.type'].search([('code','=','WORK100')], limit=1)    
            data.append((0,0,{
              'payslip_id': payslip.id,
              'work_entry_type_id': att_end.id,
              'name': att_end.name,
              'number_of_days':attendance_day,
            }))
            
            """Leave Count"""
            leaves = self.env['hr.leave'].search([('employee_id','=',payslip.employee_id.id),('date_from','>=',payslip.date_from),('date_to','<=',payslip.date_to),('state','=','validate')])
            leave_day=0
            
            for lv in leaves:
                leave_day += lv.number_of_days
            lv_end = self.env['hr.work.entry.type'].search([('code','=','LEAVE110')], limit=1)    
            data.append((0,0,{
              'payslip_id': payslip.id,
              'work_entry_type_id': lv_end.id,
              'name': lv_end.name,
              'number_of_days':leave_day,
            }))
            
            """Rest Day Count"""
            day = (payslip.date_to - payslip.date_from).days + 1
            if payslip.contract_id.date_start > payslip.date_from:
                day = (payslip.date_to - payslip.contract_id.date_start).days + 1
            start_date = payslip.date_from
            rest_day_count=0
            for ia in range(day):
                start_date = start_date + timedelta(1)
                attendance_present = self.env['resource.calendar.attendance'].sudo().search([('dayofweek','=',start_date.weekday()),('calendar_id','=',payslip.employee_id.resource_calendar_id.id)], limit=1)
                attendd=self.env['hr.attendance'].search([('employee_id' ,'=', payslip.employee_id.id),('att_date' ,'=', start_date)], limit=1) 
                remain_day = 0 
                if attendd:
                    remain_day = 1 - attendd.att_count
                if not attendance_present:
                    rest_day_count+= 1 - remain_day   
                
            rest_day_end = self.env['hr.work.entry.type'].search([('code','=','LEAVE100')], limit=1)    
            data.append((0,0,{
              'payslip_id': payslip.id,
              'work_entry_type_id': rest_day_end.id,
              'name': rest_day_end.name,
              'number_of_days':rest_day_count,
            }))
            
            """Absent Count"""
            total_days = attendance_day + leave_day + rest_day_count
            absent_day = (day - total_days)
            absent_day_end = self.env['hr.work.entry.type'].search([('code','=','OUT')], limit=1)
            if payslip.employee_id.leave_ded==False:
                data.append((0,0,{
                  'payslip_id': payslip.id,
                  'work_entry_type_id': absent_day_end.id,
                  'name': absent_day_end.name,
                  'number_of_days':absent_day,
                }))
            else:
                att_enda = self.env['hr.work.entry.type'].search([('code','=','WORK100')], limit=1)    
                data.append((0,0,{
                  'payslip_id': payslip.id,
                  'work_entry_type_id': att_enda.id,
                  'name': att_enda.name,
                  'number_of_days':absent_day,
                }))    
            payslip.worked_days_line_ids.unlink() 
            payslip.worked_days_line_ids=data
            payslip.action_leave_deduction()
           
        res = super(HrPayslip, self).compute_sheet()
        return res
   

    
    def action_leave_deduction(self):
        day = (self.date_to - self.date_from).days + 1
        start_date = self.date_from
        rest_day_count=0
        max_relaxation=self.employee_id.policy_id.number_of_late
        relxation_count=0
        for ia in range(day):
            start_date = start_date + timedelta(1)
            exist_att = self.env['hr.attendance'].search([('employee_id','=',self.employee_id.id),('att_date','=',start_date),('worked_hours','>',0)], limit=1)
            if exist_att:
                checking_date = exist_att.check_in + relativedelta(hours=+5)
                
                if str(checking_date.strftime('%H.%M')) > str(self.employee_id.policy_id.grace_period):
                    relxation_count += 1
                    if max_relaxation < relxation_count: 
                        leave_type = self.env['hr.leave.type'].search([('unpaid_leave','=',True)], limit=1)
                        leave_types = self.env['hr.leave.type'].search([('leave_priority','!=',0),('unpaid_leave','=',True)], order='leave_priority ASC')
                        for type in leave_types:
                            total_allocations = 0
                            total_leaves = 0 
                            allocation = self.env['hr.leave.allocation'].search([('employee_id','=',self.employee_id.id),('state','=','validate'),('holiday_status_id','=',type.id),('date_from','>=',self.date_from.replace(day=1, month=7)),('date_to','<=',self.date_to.replace(day=30, month=6))])
                            leaves = self.env['hr.leave'].search([('employee_id','=',self.employee_id.id),('state','=','validate'),('holiday_status_id','=',type.id),('request_date_from','>=',self.date_from.replace(day=1, month=7)),('request_date_to','<=',self.date_from.replace(day=30, month=6)) ])
                            for alloc in allocation:
                                total_allocations += alloc.number_of_days
                            for leav in leaves:
                                total_leaves += leav.number_of_days                                              
                            remaining_alloc =  total_allocations - total_leaves   
                            if   total_allocations >  total_leaves and remaining_alloc > self.employee_id.policy_id.leave_ded: 
                                leave_type = type
                                break;
                        leaves = self.env['hr.leave'].search([('employee_id','=',self.employee_id.id),('request_date_from','>=',start_date ),('request_date_to' ,'<=', start_date) ])
                        if leaves:
                            pass
                        else:
                            line_vals = {
                                'employee_id': self.employee_id.id,
                                'number_of_days': self.employee_id.policy_id.leave_ded,
                                'date_from': exist_att.check_in,
                                'date_to': exist_att.check_in + relativedelta(hours=+4),
                                'request_date_from': exist_att.att_date,
                                'request_date_to': exist_att.att_date,
                                'holiday_status_id': leave_type.id,
                                'name': 'Leave Deduction Due To Late Arrival',
                            }
                            leave = self.env['hr.leave'].create(line_vals)
                            leave.update({
                                'number_of_days': self.employee_id.policy_id.leave_ded,
                            })
                            leave.action_approve()
                            if leave.state!='validate':
                                leave.action_validate()
            
