from odoo import models, fields, api, _
from  odoo import models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class StockMovementReport(models.AbstractModel):
    _name = 'report.ws_material_request_report.mvt_xlx'
    _description = 'Stock Movement Report'
    _inherit = 'report.report_xlsx.abstract'
    
    
    def generate_xlsx_report(self, workbook, data, lines):
        docs = self.env['stock.movement.wizard'].browse(self.env.context.get('active_id'))
        sheet = workbook.add_worksheet('Stock Movement Report')
        bold = workbook. add_format({'bold': True, 'align': 'center','bg_color': '#FFFF99','border': True})
        title = workbook.add_format({'bold': True, 'align': 'center', 'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border':True,})
        format2 = workbook.add_format({'align': 'center'})
        format3 = workbook.add_format({'align': 'center','bold': True,'border': True,})
        sheet.write(0, 1,'DATE FROM ' ,title)
        sheet.write(0, 2, str(docs.date_from.strftime('%d-%m-%Y')) ,title)

        sheet.write(1, 1, 'DATE TO ' ,title)
        sheet.write(1, 2, str(docs.date_to.strftime('%d-%m-%Y')) ,title)
        
        sheet.write(0,4, 'LOCATION ' ,title)
        sheet.write(0, 5, str([loc.name for loc in docs.location_ids]) ,title)

        sheet.write(0, 7,  'CATEGORY ' ,title)
        sheet.write(0, 8, str(docs.categ_id.name if docs.categ_id else '-') ,title)
        
        sheet.set_column(1, 38, 20)
        total_amount_sum= 0  
        total_qty_done= 0
        
        sheet.write(3, 0, '', header_row_style)
        sheet.write(3, 1, '', header_row_style)
        sheet.write(3, 2, '', header_row_style)
        sheet.write(3, 3, '', header_row_style)
        sheet.write(3, 4, '', header_row_style)
        sheet.write(3, 5, '', header_row_style)
        sheet.write(3, 6, '', header_row_style)
        sheet.write(3, 7, '', header_row_style)
        sheet.write(3, 8, '', header_row_style)
        
        #Opening Stock
        sheet.merge_range(3,9, 3,11, 'Opening Stock', header_row_style)       
        #Purchases
        sheet.merge_range(3,12, 3,14, 'Purchases', header_row_style)
        #Transfer In
        sheet.merge_range(3,15, 3,17, 'Transfer In', header_row_style)
        #Sales Return
        sheet.merge_range(3,18, 3,20, 'Sales Return', header_row_style)
        #Sales
        sheet.merge_range(3,21, 3,25, 'Sales', header_row_style)
        #Transfer Out
        sheet.merge_range(3,27, 3,28, 'Transfer Out', header_row_style)
        #Adjustment
        sheet.merge_range(3,29, 3,31, 'Adjustment', header_row_style)        
        #Closing Stock
        sheet.merge_range(3,32, 3,34, 'Closing Stock', header_row_style)
        #Stock in Transit
        sheet.merge_range(3,35, 3,37, 'Stock in Transit', header_row_style)        
        
        sheet.write(4, 0, 'SR#', header_row_style)
        sheet.write(4, 1, 'Item Code', header_row_style)
        sheet.write(4, 2, 'Item Description', header_row_style)
        sheet.write(4, 3, 'Category', header_row_style)
        sheet.write(4, 4, 'Season', header_row_style)
        sheet.write(4, 5, 'Color', header_row_style)
        sheet.write(4, 6, 'Size', header_row_style)
        sheet.write(4, 7, 'UOM', header_row_style)
        sheet.write(4, 8, 'Retail Price', header_row_style)
        #Opening Stock
        sheet.write(4, 9, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 10, 'Cost Price', header_row_style)
        sheet.write(4, 11, 'Amount', header_row_style)
        #Purchases
        sheet.write(4, 12, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 13, 'Cost Price', header_row_style)
        sheet.write(4, 14, 'Amount', header_row_style)
        #Transfer In
        sheet.write(4, 15, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 16, 'Cost Price', header_row_style)
        sheet.write(4, 17, 'Amount', header_row_style)
        #Sales Return
        sheet.write(4, 18, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 19, 'Cost Price', header_row_style)
        sheet.write(4, 20, 'Amount', header_row_style)
        #Sales
        sheet.write(4, 21, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 22, 'Cost Price', header_row_style)
        sheet.write(4, 23, 'Amount', header_row_style)
        sheet.write(4, 24, 'Net Sales Amount', header_row_style)
        sheet.write(4, 25, 'Sales Tax', header_row_style)
        #Transfer Out
        sheet.write(4, 26, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 27, 'Cost Price', header_row_style)
        sheet.write(4, 28, 'Amount', header_row_style)
        #Adjustment
        sheet.write(4, 29, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 30, 'Cost Price', header_row_style)
        sheet.write(4, 31, 'Amount', header_row_style)
        #Closing Stock
        sheet.write(4, 32, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 33, 'Cost Price', header_row_style)
        sheet.write(4, 34, 'Amount', header_row_style)
        #stock in Transit
        sheet.write(4, 35, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 36, 'Cost Price', header_row_style)
        sheet.write(4, 37, 'Amount', header_row_style)
        
        sr_no=1
        row=5
        
        sheet.write(row, 0, str(), header_row_style)
        sheet.write(row, 1, str(), header_row_style)
        sheet.write(row, 2, str(), header_row_style)
        sheet.write(row, 3, str(), header_row_style)
        sheet.write(row, 4, str(), header_row_style)
        sheet.write(row, 5, str(), header_row_style)
        sheet.write(row, 6, str(), header_row_style)
        sheet.write(row, 7, str(), header_row_style)
        sheet.write(row, 8, str(), header_row_style)
        #Opening Stock
        sheet.write(row, 9,str(), header_row_style)
        sheet.write(row, 10, str(), header_row_style)
        sheet.write(row, 11, str(), header_row_style)
        #Purchases
        sheet.write(row, 12, str(), header_row_style)
        sheet.write(row, 13, str(), header_row_style)
        sheet.write(row, 14, str(), header_row_style)
        #Transfer In
        sheet.write(row, 15, str(), header_row_style)
        sheet.write(row, 16, str(), header_row_style)
        sheet.write(row, 17, str(), header_row_style)
        #Sales Return
        sheet.write(row, 18, str(), header_row_style)
        sheet.write(row, 19, str(), header_row_style)
        sheet.write(row, 20, str(), header_row_style)
        #Sales
        sheet.write(row, 21, str(), header_row_style)
        sheet.write(row, 22, str(), header_row_style)
        sheet.write(row, 23, str(), header_row_style)
        sheet.write(row, 24, str(), header_row_style)
        sheet.write(row, 25, str(), header_row_style)
        #Transfer Out
        sheet.write(row, 26, str(), header_row_style)
        sheet.write(row, 27, str(), header_row_style)
        sheet.write(row, 28, str(), header_row_style)
        #Adjustment
        sheet.write(row, 29, str(), header_row_style)
        sheet.write(row, 30, str(), header_row_style)
        sheet.write(row, 31, str(), header_row_style)
        #Closing Stock
        sheet.write(row, 32, str(), header_row_style)
        sheet.write(row, 33, str(), header_row_style)
        sheet.write(row, 34, str(), header_row_style)
        #stock in Transit
        sheet.write(row, 35, str(), header_row_style)
        sheet.write(row, 36, str(), header_row_style)
        sheet.write(row, 37, str(), header_row_style)
        
        #Total
        sheet.write(row, 0, str(), header_row_style)
        sheet.write(row, 1, str(), header_row_style)
        sheet.write(row, 2, str(), header_row_style)
        sheet.write(row, 3, str(), header_row_style)
        sheet.write(row, 4, str(), header_row_style)
        sheet.write(row, 5, str(), header_row_style)
        sheet.write(row, 6, str(), header_row_style)
        sheet.write(row, 7, str(), header_row_style)
        sheet.write(row, 8, str(), header_row_style)
        #Opening Stock
        sheet.write(row, 9,str(), header_row_style)
        sheet.write(row, 10, str(), header_row_style)
        sheet.write(row, 11, str(), header_row_style)
        #Purchases
        sheet.write(row, 12, str(), header_row_style)
        sheet.write(row, 13, str(), header_row_style)
        sheet.write(row, 14, str(), header_row_style)
        #Transfer In
        sheet.write(row, 15, str(), header_row_style)
        sheet.write(row, 16, str(), header_row_style)
        sheet.write(row, 17, str(), header_row_style)
        #Sales Return
        sheet.write(row, 18, str(), header_row_style)
        sheet.write(row, 19, str(), header_row_style)
        sheet.write(row, 20, str(), header_row_style)
        #Sales
        sheet.write(row, 21, str(), header_row_style)
        sheet.write(row, 22, str(), header_row_style)
        sheet.write(row, 23, str(), header_row_style)
        sheet.write(row, 24, str(), header_row_style)
        sheet.write(row, 25, str(), header_row_style)
        #Transfer Out
        sheet.write(row, 26, str(), header_row_style)
        sheet.write(row, 27, str(), header_row_style)
        sheet.write(row, 28, str(), header_row_style)
        #Adjustment
        sheet.write(row, 29, str(), header_row_style)
        sheet.write(row, 30, str(), header_row_style)
        sheet.write(row, 31, str(), header_row_style)
        #Closing Stock
        sheet.write(row, 32, str(), header_row_style)
        sheet.write(row, 33, str(), header_row_style)
        sheet.write(row, 34, str(), header_row_style)
        #stock in Transit
        sheet.write(row, 35, str(), header_row_style)
        sheet.write(row, 36, str(), header_row_style)
        sheet.write(row, 37, str(), header_row_style)        
            