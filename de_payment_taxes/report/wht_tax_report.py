# -*- coding: utf-8 -*-

import json
from odoo import models
from odoo.exceptions import UserError


class WHTTaxReport(models.Model):
    _name = 'report.de_payment_taxes.wht_tax_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        data = self.env['wht.report.wizard'].browse(self.env.context.get('active_id'))
        format1 = workbook.add_format({'font_size': '12', 'align': 'left', 'bold': True})
        format_right = workbook.add_format({'font_size': '12', 'align': 'right'})
        format_left = workbook.add_format({'font_size': '12', 'align': 'left'})
        format_total = workbook.add_format({'font_size': '12', 'align': 'right', 'bold': True,'border': True})
        sheet2 = workbook.add_worksheet('Details Report')
        bold = workbook. add_format({'bold': True, 'align': 'center','border': True})
        sr_no = 1
        row = 1
        
       
        sheet2.write(0, 1, str(data.company_id.name), bold)
        sheet2_row=4
        sheet2.write(3, 0, 'SR#', bold)
        sheet2.write(3, 1, 'Vendor Name', bold)
        sheet2.write(3, 2, 'NTN', format1)
        sheet2.write(3, 3, 'Invoive No', bold)
        sheet2.write(3, 4, 'Transiction Date', bold)
        sheet2.write(3, 5, 'Gross Amount', bold)
        sheet2.write(3, 6, 'Invoice Amount', bold)
        sheet2.write(3, 7, 'Taxable Amount', bold)
        sheet2.write(3, 8, 'Payment', bold)
        sheet2.write(3, 9, 'Rate', bold)
        sheet2.write(3, 10, 'WHT Amount', bold)
        sheet2.write(3, 11, 'Amount Paid', bold)
       
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
        sheet2_sr_no=1
        total_gross_amt =0
        total_inv_amt =0
        total_taxable_amt=0
        total_payment_amt=0 
        total_wht_amt=0
        total_amt_paid_amt=0
        payments = self.env['account.payment'].search([('state','=','posted'),('total_wht_tax_amount','!=',0),('date','>=',data.date_from),('date','<=',data.date_to)])
        for pay in payments:
            sheet2.write(sheet2_row, 0, sheet2_sr_no, format_right)
            sheet2.write(sheet2_row, 1, str(pay.partner_id.name), format_left)
            sheet2.write(sheet2_row, 2, str(pay.partner_id.vat), format_right)
            sheet2.write(sheet2_row, 3, str(pay.name), format_right)
            sheet2.write(sheet2_row, 4, str(pay.date.strftime('%d-%b-%y')), format_left)
            sheet2.write(sheet2_row, 5, str('{0:,}'.format(int(round(pay.amount+pay.total_wht_tax_amount)))), format_left)
            total_gross_amt += pay.amount+pay.total_wht_tax_amount
            sheet2.write(sheet2_row, 6, str('{0:,}'.format(int(round(pay.amount+pay.total_wht_tax_amount)))), format_right)
            total_inv_amt += pay.amount+pay.total_wht_tax_amount
            sheet2.write(sheet2_row, 7, str('{0:,}'.format(int(round(pay.amount+pay.total_wht_tax_amount)))), format_left)
            total_taxable_amt += pay.amount+pay.total_wht_tax_amount
            sheet2.write(sheet2_row, 8, str('{0:,}'.format(int(round(pay.amount)))), format_right)
            total_payment_amt += pay.amount
            sheet2.write(sheet2_row, 9, str(pay.wht_percentage), format_right)
            sheet2.write(sheet2_row, 10, str('{0:,}'.format(int(round(pay.total_wht_tax_amount)))), format_left)
            total_wht_amt += pay.total_wht_tax_amount
            sheet2.write(sheet2_row, 11, str('{0:,}'.format(int(round(pay.amount)))), format_right)
            total_amt_paid_amt += pay.amount
            sheet2_row+=1
            sheet2_sr_no+=1
        
        sheet2.write(sheet2_row, 0, str(), format_right)
        sheet2.write(sheet2_row, 1, str(), format_left)
        sheet2.write(sheet2_row, 2, str(), format_right)
        sheet2.write(sheet2_row, 3, str(), format_right)
        sheet2.write(sheet2_row, 4, str(), format_left)
        sheet2.write(sheet2_row, 5, str('{0:,}'.format(int(round(total_gross_amt)))), bold)
        sheet2.write(sheet2_row, 6, str('{0:,}'.format(int(round(total_inv_amt)))), bold)
        sheet2.write(sheet2_row, 7, str('{0:,}'.format(int(round(total_taxable_amt)))), bold)
        sheet2.write(sheet2_row, 8, str('{0:,}'.format(int(round(total_payment_amt)))), bold)
        sheet2.write(sheet2_row, 9, str(), bold)
        sheet2.write(sheet2_row, 10, str('{0:,}'.format(int(round(total_wht_amt)))), bold)
        sheet2.write(sheet2_row, 11, str('{0:,}'.format(int(round(total_amt_paid_amt)))), bold)
                
                
        
            
            
            
            


