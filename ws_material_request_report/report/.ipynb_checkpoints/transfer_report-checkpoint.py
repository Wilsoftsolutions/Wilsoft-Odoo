from odoo import models, fields, api, _
from  odoo import models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class TransferReport(models.AbstractModel):
    _name = 'report.ws_material_request_report.trans_xlx'
    _description = 'Transfer Report'
    _inherit = 'report.report_xlsx.abstract'
    
    
    def generate_xlsx_report(self, workbook, data, lines):
        docs = self.env['transfer.report.wizard'].browse(self.env.context.get('active_id'))
        sheet = workbook.add_worksheet('Transfer Report')
        bold = workbook. add_format({'bold': True, 'align': 'center','bg_color': '#FFFF99','border': True})
        title = workbook.add_format({'bold': True, 'align': 'center', 'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border':True})
        format2 = workbook.add_format({'align': 'center'})
        format3 = workbook.add_format({'align': 'center','bold': True,'border': True,})
        sheet.write(0, 1,'DATE FROM ' ,title)
        sheet.write(0, 2, str(docs.date_from.strftime('%d-%m-%Y')) ,title)

        sheet.write(1, 1, 'DATE TO ' ,title)
        sheet.write(1, 2, str(docs.date_to.strftime('%d-%m-%Y')) ,title)
        
        sheet.write(0,4, 'LOCATION ' ,title)
        sheet.write(0, 5, str([loc.name for loc in docs.location_ids]) ,title)

        sheet.write(0, 7,  'CATEGORY ' ,title)
        sheet.write(0, 8, str(docs.categ_id.name) ,title)
        sheet.set_column(1, 28, 20)
        total_amount_sum= 0  
        total_qty_done= 0
        sheet.write(3, 0, 'SR#', header_row_style)
        sheet.write(3, 1, 'Location', header_row_style)
        sheet.write(3, 2, 'Item Code', header_row_style)
        sheet.write(3, 3, 'Item Description', header_row_style)
        sheet.write(3, 4, 'Category', header_row_style)
        sheet.write(3, 5, 'Season', header_row_style)
        sheet.write(3, 6, 'Color', header_row_style)
        sheet.write(3, 7, 'Size', header_row_style)
        sheet.write(3, 8, 'UOM', header_row_style)
        sheet.write(3, 9, 'Transfer Order #', header_row_style)
        sheet.write(3, 10, 'Transfer From Location', header_row_style)
        sheet.write(3, 11, 'Transfer To Location', header_row_style)
        sheet.write(3, 12, 'Qty (Pairs)', header_row_style)
        sheet.write(3, 13, 'Cost Price', header_row_style)
        sheet.write(3, 14, 'Amount', header_row_style)
        sr_no=1
        row=4
        move_lines = self.env['stock.move.line']
        transfers = move_lines.search([('date','>=',docs.date_from),('date','<=',docs.date_to)], order='date DESC')
        if docs.categ_id and docs.location_ids:
            transfers = move_lines.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('product_id.categ_id','=',docs.categ_id.id),('location_id','in',docs.location_ids.ids)], order='date DESC')
        elif docs.categ_id:
            transfers = move_lines.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('product_id.categ_id','=',docs.categ_id.id)], order='date DESC')
        elif  docs.location_ids:
            transfers = move_lines.search([('date','>=',docs.date_from),('date','<=',docs.date_to),('location_id','in',docs.location_ids.ids)], order='date DESC')
        for line in transfers:  
            sheet.write(row, 0, str(sr_no), format2)
            sheet.write(row, 1, str(line.location_id.name), format2)
            sheet.write(row, 2, str(line.product_id.default_code if line.product_id.default_code else '-'), format2)
            sheet.write(row, 3, str(line.product_id.name if line.product_id else '-'), format2)
            sheet.write(row, 4, str(line.product_id.categ_id.name if line.product_id else '-'), format2)
            sheet.write(row, 5, str(line.product_id.season if line.product_id.season else '-'), format2)
            color=''
            size=''
            inner_count=0
            for attr in line.product_id.product_template_variant_value_ids:
                inner_count+=1
                if inner_count==1:
                    color=attr.name
                if inner_count==2:  
                    size=attr.name 
                
            sheet.write(row, 6, str(color), format2)
            sheet.write(row, 7, str(size), format2)
            sheet.write(row, 8, str(line.product_id.uom_id.name), format2)
            sheet.write(row, 9, str(line.move_id.picking_id.name), format2)
            sheet.write(row, 10, str(line.location_id.name), format2)
            sheet.write(row, 11, str(line.location_dest_id.name), format2)
            sheet.write(row, 12, str(line.qty_done), format2)
            total_qty_done += line.qty_done
            sheet.write(row, 13, str('{0:,}'.format(int(round( line.product_id.standard_price)))), format2)
            sheet.write(row, 14, str('{0:,}'.format(int(round( line.product_id.standard_price * line.qty_done)))), format2)
            total_amount_sum += line.product_id.standard_price * line.qty_done
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
        sheet.write(row, 8, str(), header_row_style)
        sheet.write(row, 9, str(), header_row_style)
        sheet.write(row, 10, str(), header_row_style)
        sheet.write(row, 11, str() , header_row_style)
        sheet.write(row, 12, str('{0:,}'.format(int(round(total_qty_done)))), header_row_style)
        sheet.write(row, 13, str() , header_row_style)
        sheet.write(row, 14, str('{0:,}'.format(int(round(total_amount_sum)))), header_row_style)
        
                
            