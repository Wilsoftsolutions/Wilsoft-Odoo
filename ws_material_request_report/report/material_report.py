from odoo import models, fields, api, _
from  odoo import models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class TransferReport(models.AbstractModel):
    _name = 'report.ws_material_request_report.mtreq_xlx'
    _description = 'Transfer Report'
    _inherit = 'report.report_xlsx.abstract'
    
    
    def generate_xlsx_report(self, workbook, data, lines):
        docs = self.env['material.report.wizard'].browse(self.env.context.get('active_id'))
        sheet = workbook.add_worksheet('Claim Report')
        bold = workbook. add_format({'bold': True, 'align': 'center','bg_color': '#FFFF99','border': True})
        title = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 15, 'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border':True})
        format2 = workbook.add_format({'align': 'center'})
        format3 = workbook.add_format({'align': 'center','bold': True,'border': True,})
        sheet.write('C1:D1', (self.env.company.name) ,title)
        sheet.write('C2:D2', 'Claim Report' ,title)
        sheet.write('E1:E1', 'DATE FROM '+str(docs.date_from.strftime('%d-%m-%Y')) ,title)
        sheet.write('E2:E2', 'DATE TO '+str(docs.date_to.strftime('%d-%m-%Y')) ,title)
        sheet.set_column(1, 21, 20)
        subtotal_day_amount=0  
        sheet.write(3, 0, 'SR#', header_row_style)
        sheet.write(3, 1, 'Date', header_row_style)
        sheet.write(3, 2, 'Customer', header_row_style)
        sheet.write(3, 3, 'City', header_row_style)
        sheet.write(3, 4, 'Claim Remarks', header_row_style)
        sheet.write(3, 5, 'Q.C Remarks', header_row_style)
        sheet.write(3, 6, 'Article', header_row_style)
        sheet.write(3, 7, 'Qty', header_row_style)
        sheet.write(3, 8, 'Amount', header_row_style)
        sheet.write(3, 9, 'State', header_row_style)
        sheet.write(3, 10, 'Current Loaction', header_row_style)
        sheet.write(3, 11, 'Vendor', header_row_style)
        sheet.write(3, 12, 'Discription', header_row_style)
        sr_no=1
        row=4
        claimsprice=self.env['claimed.form']
        claims = claimsprice.search([('date','>=',docs.date_from),('date','<=',docs.date_to)], order='date DESC')
        if docs.partner_id and docs.status:
            claims = claimsprice.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('customer_id','=',docs.partner_id.id),('state','=',docs.status)], order='date DESC')
        elif docs.partner_id:
            claims = claimsprice.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('customer_id','=',docs.partner_id.id)], order='date DESC')
        elif  docs.status:
            claims = claimsprice.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('state','=',docs.status)], order='date DESC')
        for claim in claims:  
            for line in claim.claimed_line_ids:
                sheet.write(row, 0, str(sr_no), format2)
                sheet.write(row, 1, str(line.claimed_id.date.strftime('%d-%b-%Y')), format2)
                sheet.write(row, 2, str(line.claimed_id.customer_id.name if line.claimed_id.customer_id else '-'), format2)
                sheet.write(row, 3, str(line.claimed_id.city if line.claimed_id.city else '-'), format2)
                sheet.write(row, 4, str(line.claimed_id.claimed_remark.name if line.claimed_id.claimed_remark else '-'), format2)
                sheet.write(row, 5, str(line.claimed_id.qc_remark.qc_remark if line.claimed_id.qc_remark else '-'), format2)
                sheet.write(row, 6, str(line.p_id.name if line.p_id else '-'), format2)
                sheet.write(row, 7, str(line.qty), format2)
                sheet.write(row, 8, str('{0:,}'.format(int(round(line.sub_total)))), format2)
                subtotal_day_amount+=line.sub_total 
                sheet.write(row, 9, str(line.claimed_id.state if line.claimed_id.state else '-'), format2)
                sheet.write(row, 10, str(line.claimed_id.current_location if line.claimed_id.current_location else '-'), format2)
                sheet.write(row, 11, str(line.claimed_id.x_studio_vendor.name if line.claimed_id.x_studio_vendor else '-'), format2)
                sheet.write(row, 12, str(line.claimed_id.description if line.claimed_id.description else '-'), format2)               
                sr_no+=1
                row+=1              
        sheet.write(row, 0, str(), header_row_style)
        sheet.write(row, 1, str(), header_row_style)
        sheet.write(row, 2, str() , header_row_style)
        sheet.write(row, 3, str(), header_row_style)
        sheet.write(row, 4, str(), header_row_style)
        sheet.write(row, 5, str(), header_row_style)
        sheet.write(row, 6, str() , header_row_style)
        sheet.write(row, 7, str(), header_row_style)
        sheet.write(row, 8, str('{0:,}'.format(int(round(subtotal_day_amount)))), header_row_style)
        sheet.write(row, 9, str(), header_row_style)
        sheet.write(row, 10, str(), header_row_style)
        sheet.write(row, 11, str() , header_row_style)
        sheet.write(row, 12, str(), header_row_style)
        
                
            