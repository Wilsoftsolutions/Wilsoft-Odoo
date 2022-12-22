# -*- coding: utf-8 -*-

import json
from odoo import models
from odoo.exceptions import UserError


class BatchslipDetail(models.Model):
    _name = 'report.de_hr_payroll_policy.batch_detail_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        data = self.env['batch.slip.report'].browse(self.env.context.get('active_id'))
        format1 = workbook.add_format({'font_size': '12', 'align': 'left', 'bold': True})
        format_right = workbook.add_format({'font_size': '12', 'align': 'right'})
        format_left = workbook.add_format({'font_size': '12', 'align': 'left'})
        format_total = workbook.add_format({'font_size': '12', 'align': 'right', 'bold': True,'border': True})
        sheet2 = workbook.add_worksheet('Details Report')
        bold = workbook. add_format({'bold': True, 'align': 'center','border': True})
        sr_no = 1
        row = 1
        
        employees=self.env['hr.employee'].search([('company_id','=',data.company_id.id)])
            
        extra_payroll_rule= self.env['hr.salary.rule'].search([('detail_report','=',True),('detail_deduction','!=',True),('detail_compansation','!=',True)], order='detail_sequence asc')

        deduction_rule= self.env['hr.salary.rule'].search([('detail_deduction','=',True)], order='detail_sequence asc')
        compansation_rule= self.env['hr.salary.rule'].search([('detail_compansation','=',True)], order='detail_sequence asc')
        deduction_rule_list=[]
        compansation_rule_list=[]
        extra_rule_list=[]    
        for extra_rule in extra_payroll_rule:
            extra_rule_amount=0
            for emp in employees:
                payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                for extra_slip in payslips:
                    for extra_slip_rule in extra_slip.line_ids:
                        if extra_slip_rule.salary_rule_id.id==extra_rule.id:
                            extra_rule_amount +=   extra_slip_rule.amount 
            if extra_rule_amount !=0:
                extra_rule_list.append(extra_rule.id)        
        for comp_rule in compansation_rule:
            comp_rule_amount=0
            for emp in employees:
                payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                for compansation_slip in payslips:
                    for compansation_rule in compansation_slip.line_ids:
                        if compansation_rule.salary_rule_id.id==comp_rule.id:
                            comp_rule_amount +=   compansation_rule.amount  
                        
            if comp_rule_amount !=0:
                compansation_rule_list.append(comp_rule.id)
                
        for ded_rule in deduction_rule:
            ded_rule_amount=0
            for emp in employees:
                payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                for ded_slip in payslips:
                    for deduction_rule in ded_slip.line_ids:
                        if deduction_rule.salary_rule_id.id==ded_rule.id:
                            ded_rule_amount +=   deduction_rule.amount  
                        
            if ded_rule_amount !=0:
                deduction_rule_list.append(ded_rule.id)  
         
        uniq_compansation_rule_list = set(compansation_rule_list)   
        uniq_deduction_rule_list = set(deduction_rule_list) 
        uniq_extra_rule_list = set(extra_rule_list) 
        uniq_deduction_rule= self.env['hr.salary.rule'].search([('id','in',list(uniq_deduction_rule_list))], order='detail_sequence asc')
        uniq_compansation_rule= self.env['hr.salary.rule'].search([('id','in',list(uniq_compansation_rule_list))], order='detail_sequence asc')
        uniq_extra_rule= self.env['hr.salary.rule'].search([('id','in',list(uniq_extra_rule_list))], order='detail_sequence asc')
        

        sheet2_row=1
        sheet2.write(0, 0, 'SR#', format1)
        sheet2.write(0, 1, 'Employee Code', format1)
        sheet2.write(0, 2, 'Name', format1)
        sheet2.write(0, 3, 'Designation', format1)
        sheet2.write(0, 4, 'Department', format1)
        sheet2.write(0, 5, 'Grade', format1)
        sheet2.write(0, 6, 'Date Of Joining', format1)
        sheet2.write(0, 7, 'Location', format1)
        sheet2.write(0, 8, 'Lvs Ded Days', format1)
        sheet2.write(0, 9, 'Joining Ded Days', format1)
       
        sheet2.set_column(0, 0, 5)
        sheet2.set_column(1, 1, 15)
        sheet2.set_column(2, 2, 5)
        sheet2.set_column(3, 3, 20)
        sheet2.set_column(4, 5, 10)
        sheet2.set_column(6, 6, 5)
        sheet2.set_column(7, 7, 20)
        sheet2.set_column(8, 9, 10)
        sheet2.set_column(10, 10, 20)
        sheet2.set_column(11, 12, 10)
        sheet2.set_column(13, 13, 15)
        sheet2.set_column(12, 12, 13)
        sheet2.set_column(14, 17, 15)
        sheet2.set_column(18, 18, 5)
        sheet2.set_column(19, 19, 10)
        sheet2.set_column(20, 50, 20)
        extra_col = 10
        total_ovt_hours = 0
        uniq_ext_rule = 0
        uniq_ext_loop_detail=0
        for extra in uniq_extra_rule:
            if uniq_ext_loop_detail==extra.detail_label:
                pass
            else:    
                sheet2.write(0, extra_col, str(extra.detail_label), format1)
                extra_col += 1
            uniq_ext_loop_detail=extra.detail_label
            
        comp_col = extra_col
        uniq_comp_loop_detail=0
        for comp in uniq_compansation_rule:
            if uniq_comp_loop_detail==comp.detail_label:
                pass
            else:
                sheet2.write(0, comp_col, str(comp.detail_label), format1)
                comp_col += 1
            uniq_comp_loop_detail=comp.detail_label
            
        sheet2.write(0, comp_col, 'Total', format1)
        comp_col += 1
        ded_col = comp_col
        uniq_ded_loop_detail=0
        for ded in uniq_deduction_rule:
            if uniq_ded_loop_detail==ded.detail_label:
                pass
            else:
                sheet2.write(0, ded_col, str(ded.detail_label), format1)
                ded_col += 1
            uniq_ded_loop_detail=ded.detail_label
        
        sheet2.write(0, ded_col, 'Tot.Ded', format1)
        ded_col += 1
        sheet2.write(0, ded_col, 'Net Payable', format1)
        
        sheet2_sr_no = 1
        total_net_payable_sheet2 = 0
        grand_total_compansation_amount = 0
        grand_total_deduction_amount = 0
        for emp in employees:
            payslips = self.env['hr.payslip'].search(
                [('employee_id', '=', emp.id), ('date_to', '>=', data.date_from), ('date_to', '<=', data.date_to),('state','in',('verify','done','paid'))], order='date_to ASC')
            if payslips:
                cost_center = '-'
                cost_account = '-'
                absent_days = 0
                working_days = 0
                net_payable_sheet2 = 0
                contract = self.env['hr.contract'].search([ ('employee_id','=',emp.id),('state','=','open')], limit=1)
                if not contract:
                    contract = self.env['hr.contract'].search([ ('employee_id','=',emp.id)], limit=1)
                salary_month = 0

                for slip in payslips:
                    salary_month += 1
                    contract = slip.contract_id
                    for sheet2_rule_line in slip.line_ids:
                        if sheet2_rule_line.code=='NET':
                            net_payable_sheet2 += sheet2_rule_line.amount
                    working_days += (slip.date_to-slip.date_from).days+1
                    for workday in slip.worked_days_line_ids:
                        if workday.work_entry_type_id.code == "ABSENT100":
                            absent_days += workday.number_of_days
                payable_days =  (working_days - absent_days)
                if  payable_days < 0:
                    payable_days = 0
                if emp.leave_ded==True:
                    payable_days = working_days

                sheet2.write(sheet2_row, 0, sheet2_sr_no, format_right)
                sheet2.write(sheet2_row, 1, str(emp.registration_number), format_left)
                sheet2.write(sheet2_row, 2, str(emp.name), format_right)
                sheet2.write(sheet2_row, 3, str(emp.job_id.name), format_right)
                sheet2.write(sheet2_row, 4, str(emp.department_id.name), format_left)
                sheet2.write(sheet2_row, 5, str(emp.x_studio_grade), format_left)
                sheet2.write(sheet2_row, 6, str(emp.x_studio_doj), format_right)
                sheet2.write(sheet2_row, 7, str(), format_left)
                sheet2.write(sheet2_row, 8, str(), format_right)
                sheet2.write(sheet2_row, 9, str(), format_right)
                
                sheet2_extra_col = 10
                extra_amount = 0
                extra_line_duplicate = 0
                for extra_value in uniq_extra_rule:
                    if extra_value.detail_sequence==extra_line_duplicate:
                        payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                        for slip in payslips:
                            for sheet2_extra_rule in slip.line_ids:
                                if extra_value.id == sheet2_extra_rule.salary_rule_id.id:
                                    extra_amount += sheet2_extra_rule.amount
                    else: 
                        # if extra_amount>0:
                        sheet2.write(sheet2_row, sheet2_extra_col, str('{0:,}'.format(int(round(extra_amount))) if extra_amount !=0 else '-'), format_right)
                        sheet2_extra_col +=1
                        extra_amount = 0
                        extra_line_duplicate = extra_value.detail_sequence
                        payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                        for slip in payslips:
                            for sheet2_extra_rule in slip.line_ids:
                                if extra_value.id == sheet2_extra_rule.salary_rule_id.id:
                                    extra_amount += sheet2_extra_rule.amount
                                
                    

                sheet2_comp_col = sheet2_extra_col
                total_compansation_amount = 0
                total_deduction_amount = 0
                comp_line_duplicate = 0
                comp_amount = 0
                for comp_value in uniq_compansation_rule:
                    if comp_line_duplicate==comp_value.detail_sequence:
                        payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                        for slip in payslips:
                            for sheet2_rule in slip.line_ids:
                                if comp_value.id == sheet2_rule.salary_rule_id.id:
                                    comp_amount += sheet2_rule.amount
                    else:   
                        # if comp_amount>0:
                        sheet2.write(sheet2_row, sheet2_comp_col, str('{0:,}'.format(int(round(comp_amount))) if comp_amount !=0 else '-'), format_right)
                        total_compansation_amount += comp_amount
                        sheet2_comp_col += 1
                        comp_amount = 0
                        comp_line_duplicate = comp_value.detail_sequence
                        payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                        for slip in payslips:
                            for sheet2_rule in slip.line_ids:
                                if comp_value.id == sheet2_rule.salary_rule_id.id:
                                    comp_amount += sheet2_rule.amount
                                    
                sheet2.write(sheet2_row, sheet2_comp_col, str('{0:,}'.format(int(round(total_compansation_amount)))), format_right)
                grand_total_compansation_amount +=round(total_compansation_amount)
                sheet2_comp_col += 1
                sheet2_ded_col = sheet2_comp_col
                ded_line_duplicate = 0
                ded_amount=0
                for ded_value in uniq_deduction_rule:
                    if ded_value.detail_sequence==ded_line_duplicate:
                        pass
                    else:
                        # if ded_amount>0:
                        sheet2.write(sheet2_row, sheet2_ded_col, str('{0:,}'.format(int(round(ded_amount))) if ded_amount !=0 else '-'), format_right)
                        total_deduction_amount += ded_amount
                        sheet2_ded_col += 1
                        ded_amount = 0
                        ded_line_duplicate = ded_value.detail_sequence
                        payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                        for slip in payslips:
                            for sheet2_ded_rule in slip.line_ids:
                                if ded_value.id == sheet2_ded_rule.salary_rule_id.id:
                                    ded_amount += sheet2_ded_rule.amount
                                    
                    
                    
                sheet2.write(sheet2_row, sheet2_ded_col, str('{0:,}'.format(int(round(total_deduction_amount)))), format_right)
                grand_total_deduction_amount +=round(total_deduction_amount)
                sheet2_ded_col += 1
                sheet2.write(sheet2_row, sheet2_ded_col, str('{0:,}'.format(int(round(net_payable_sheet2)))), format_right)
                total_net_payable_sheet2 +=round(net_payable_sheet2)
                sheet2_sr_no += 1
                sheet2_row += 1
            
        sheet2_row += 1
        sheet2.write(sheet2_row, 0, str(), format1)
        sheet2.write(sheet2_row, 1, str(), format1)
        sheet2.write(sheet2_row, 2, str(), format1)
        sheet2.write(sheet2_row, 3, str(), format1)
        sheet2.write(sheet2_row, 4, str(), format1)
        sheet2.write(sheet2_row, 5, str(), format1)
        sheet2.write(sheet2_row, 6, str(), format1)
        sheet2.write(sheet2_row, 7, str(), format1)
        sheet2.write(sheet2_row, 8, str(), format1)
        sheet2.write(sheet2_row, 9, str(), format1)
       
        grand_total_compansation_amount_list = []
        grand_total_deduction_amount_list = []
        grand_extra_total_amount_list = []
        grand_ded_line_duplicate = 0
        grand_extra_total_amount = 0
        for grand_extra_rule in uniq_extra_rule:
            if grand_ded_line_duplicate==grand_extra_rule.detail_sequence: 
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                    for slip in payslips:
                        for slip_extra_rule in slip.line_ids:
                            if  slip_extra_rule.salary_rule_id.id==grand_extra_rule.id:
                                grand_extra_total_amount += slip_extra_rule.amount 
            else:
                # if grand_extra_total_amount>0:
                grand_extra_total_amount_list.append(grand_extra_total_amount)
                grand_extra_total_amount = 0
                grand_ded_line_duplicate=grand_extra_rule.detail_sequence
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                    for slip in payslips:
                        for slip_extra_rule in slip.line_ids:
                            if  slip_extra_rule.salary_rule_id.id==grand_extra_rule.id:
                                grand_extra_total_amount += slip_extra_rule.amount
                
        grand_ded_total_amount = 0
        grand_ded_total_duplicate = 0
        for grand_ded_rule in uniq_deduction_rule:
            if grand_ded_rule.detail_sequence==grand_ded_total_duplicate:
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                    for slip in payslips:
                        for slip_rule in slip.line_ids:
                            if  slip_rule.salary_rule_id.id==grand_ded_rule.id:
                                grand_ded_total_amount += slip_rule.amount
            else:
                # if grand_ded_total_amount>0:
                grand_total_deduction_amount_list.append(grand_ded_total_amount) 
                grand_ded_total_duplicate = grand_ded_rule.detail_sequence  
                grand_ded_total_amount = 0
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])
                    for slip in payslips:
                        for slip_rule in slip.line_ids:
                            if  slip_rule.salary_rule_id.id==grand_ded_rule.id:
                                grand_ded_total_amount += slip_rule.amount
                                
        grand_compansation_total_amount = 0
        grand_comp_total_duplicate = 0                
        for grand_rule in uniq_compansation_rule:
            if grand_rule.detail_sequence==grand_comp_total_duplicate:
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])

                    for ded_slip in payslips:
                        for ded_rule in ded_slip.line_ids:
                            if  ded_rule.salary_rule_id.id==grand_rule.id:
                                grand_compansation_total_amount += ded_rule.amount 
            else:
                # if grand_compansation_total_amount>0:
                grand_total_compansation_amount_list.append(grand_compansation_total_amount) 
                grand_compansation_total_amount = 0
                grand_comp_total_duplicate = grand_rule.detail_sequence
                for emp in employees:
                    payslips = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_to','>=',data.date_from),('date_to','<=',data.date_to),('state','in',('verify','done','paid'))])

                    for ded_slip in payslips:
                        for ded_rule in ded_slip.line_ids:
                            if  ded_rule.salary_rule_id.id==grand_rule.id:
                                grand_compansation_total_amount += ded_rule.amount     
                    
        grand_extra_col = 10 
        for grand_extra in grand_extra_total_amount_list:
            sheet2.write(sheet2_row, grand_extra_col, str('{0:,}'.format(int(round(grand_extra)))), format_total)
            grand_extra_col += 1
        grand_comp_col = grand_extra_col
        for grand_comp in grand_total_compansation_amount_list:
            sheet2.write(sheet2_row, grand_comp_col, str('{0:,}'.format(int(round(grand_comp)))), format_total)
            grand_comp_col += 1
            
        sheet2.write(sheet2_row, grand_comp_col, str('{0:,}'.format(int(round(grand_total_compansation_amount)))), format_total)
        grand_comp_col += 1
        grand_ded_col = grand_comp_col
        for grand_ded in grand_total_deduction_amount_list:
            sheet2.write(sheet2_row, grand_ded_col, str('{0:,}'.format(int(round(grand_ded)))), format_total)
            grand_ded_col += 1
        sheet2.write(sheet2_row, grand_ded_col, str('{0:,}'.format(int(round(grand_total_deduction_amount)))), format_total)
        grand_ded_col += 1
        sheet2.write(sheet2_row, grand_ded_col, str('{0:,}'.format(int(round(total_net_payable_sheet2)))), format_total)   
        
        
            
            
            
            


