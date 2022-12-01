# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    
    def compute_sheet(self):
        for payslip in self:
            data=[]
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
            leaves = self.env['hr.leave'].search([('employee_id','=',payslip.employee_id.id),('date_from','>=',payslip.date_from),('date_to','<=',payslip.date_to)])
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
            
            day = (payslip.date_to - payslip.date_from).days + 1
            start_date = payslip.date_from
            rest_day_count=0
            for ia in range(day):
                start_date = start_date + timedelta(1)
                attendance_present = self.env['resource.calendar.attendance'].sudo().search([('dayofweek','=',start_date.weekday())], limit=1)
                attendd=self.env['hr.attendance'].search([('employee_id' ,'=', payslip.employee_id.id),('att_date' ,'=', start_date)]) 
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
            total_days = attendance_day + leave_day + rest_day_count
            absent_day = (day - total_days)
            absent_day_end = self.env['hr.work.entry.type'].search([('code','=','OUT')], limit=1)    
            data.append((0,0,{
              'payslip_id': payslip.id,
              'work_entry_type_id': absent_day_end.id,
              'name': absent_day_end.name,
              'number_of_days':absent_day,
            }))
            payslip.worked_day_line_ids=data    
        res = super(HrPayslip, self).compute_sheet()
        return res
   

    
    