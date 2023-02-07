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
        opening = workbook. add_format({'bold': True,'bg_color': '#DE3163','border': True})
        purchase = workbook. add_format({'bold': True,'bg_color': '#FF7F50','border': True})
        inter_tr = workbook. add_format({'bold': True,'bg_color': '#FFBF00','border': True})
        inter_rtn = workbook. add_format({'bold': True,'bg_color': '#DFFF00','border': True})
        inter_sale = workbook. add_format({'bold': True,'bg_color': '#CCCCFF','border': True})
        inter_out = workbook. add_format({'bold': True,'bg_color': '#6495ED','border': True})
        inter_adj = workbook. add_format({'bold': True,'bg_color': '#999999','border': True})
        closing = workbook. add_format({'bold': True,'bg_color': '#FF00FF','border': True})
        transit = workbook. add_format({'bold': True,'bg_color': '#00FF00','border': True})
        title = workbook.add_format({'bold': True, 'border': True})
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
        sheet.merge_range(3,9, 3,11, 'Opening Stock', opening)       
        #Purchases
        sheet.merge_range(3,12, 3,14, 'Purchases', purchase)
        #Transfer In
        sheet.merge_range(3,15, 3,17, 'Transfer In', inter_tr)
        #Sales Return
        sheet.merge_range(3,18, 3,20, 'Sales Return', inter_rtn)
        #Sales
        sheet.merge_range(3,21, 3,24, 'Sales', inter_sale)
        #Transfer Out
        sheet.merge_range(3,25, 3,27, 'Transfer Out', inter_out)
        #Adjustment
        sheet.merge_range(3,28, 3,30, 'Adjustment', inter_adj)        
        #Closing Stock
        sheet.merge_range(3,31, 3,33, 'Closing Stock', closing)
        #Stock in Transit
        sheet.merge_range(3,34, 3,36, 'Stock in Transit', transit)        
        
        sheet.write(4, 0, 'Item Code', header_row_style)
        sheet.write(4, 1, 'Item Description', header_row_style)
        sheet.write(4, 2, 'Category', header_row_style)
        sheet.write(4, 3, 'Season', header_row_style)
        sheet.write(4, 4, 'Color', header_row_style)
        sheet.write(4, 5, 'Size', header_row_style)
        sheet.write(4, 6, 'UOM', header_row_style)
        sheet.write(4, 7, 'Retail Price', header_row_style)
        sheet.write(4, 8, 'Wholesale Price', header_row_style)
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
        #Transfer Out
        sheet.write(4, 25, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 26, 'Cost Price', header_row_style)
        sheet.write(4, 27, 'Amount', header_row_style)
        #Adjustment
        sheet.write(4, 28, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 29, 'Cost Price', header_row_style)
        sheet.write(4, 30, 'Amount', header_row_style)
        #Closing Stock
        sheet.write(4, 31, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 32, 'Cost Price', header_row_style)
        sheet.write(4, 33, 'Amount', header_row_style)
        #stock in Transit
        sheet.write(4, 34, 'Qty (Pairs)', header_row_style)
        sheet.write(4, 35, 'Cost Price', header_row_style)
        sheet.write(4, 36, 'Amount', header_row_style)
        
        sr_no=1
        row=5
        product_list = []
        move_lines = self.env['stock.move.line'] 
        products = self.env['product.product'] 
        invoices = self.env['account.move.line'] 
        quantsa = self.env['stock.quant']
        
        total_opening_qty = 0
        total_opening_list_price = 0
        total_opening_amount = 0
        
        total_closing_qty = 0
        total_closing_list_price = 0
        total_closing_amount = 0
        
        total_in_transit_qty = 0
        total_in_transit_list_price = 0
        total_in_transit_amount = 0
        
        total_adjustment_qty = 0
        total_adjustment_list_price = 0
        total_adjustment_amount = 0
        
        total_transfer_out_qty = 0
        total_transfer_out_list_price = 0
        total_transfer_out_amount = 0
        
        total_sales_qty = 0
        total_sales_list_price = 0
        total_sales_amount = 0
        total_sales_inv_amount = 0
        
        total_sale_rtn_qty = 0
        total_sale_rtn_list_price = 0
        total_sale_rtn_amount = 0
        
        total_transfer_in_qty = 0
        total_transfer_in_list_price = 0
        total_transfer_in_amount = 0
        
        total_purchase_qty = 0
        total_purchase_list_price = 0
        total_purchase_amount = 0
            
        in_stock_move_lines = move_lines.search([('location_id','=',docs.location_ids.ids),('date','>=',docs.date_from),('date','<=',docs.date_to),('state','=','done')])
        out_stock_move_lines = move_lines.search([('location_dest_id','=',docs.location_ids.ids),('date','>=',docs.date_from),('date','<=',docs.date_to),('state','=','done')])
        if docs.categ_id:
            in_stock_move_lines = move_lines.search([('product_id.categ_id','=',docs.categ_id.id),('location_id','=',docs.location_ids.ids),('date','>=',docs.date_from),('date','<=',docs.date_to),('state','=','done')])
            out_stock_move_lines = move_lines.search([('product_id.categ_id','=',docs.categ_id.id),('location_dest_id','=',docs.location_ids.ids),('date','>=',docs.date_from),('date','<=',docs.date_to),('state','=','done')])
        for  mv_line in in_stock_move_lines:  
            product_list.append(mv_line.product_id.id)
        for  mvline in out_stock_move_lines:  
            product_list.append(mvline.product_id.id)
        uniq_product_list = set(product_list)   
        for uniq_product in uniq_product_list:
            product = products.search([('id','=',uniq_product)])
            invoice_amount = 0
            sale_invoices = invoices.search([('product_id','=',uniq_product),('parent_state','=','posted'),('date','>=',docs.date_from.strftime('%Y-%m-%d')),('date','<=',docs.date_to.strftime('%Y-%m-%d'))])
            ext_invoices = [so_inv.credit for so_inv in sale_invoices]
            invoice_amount = sum(ext_invoices)
            sheet.write(row, 0, str(product.default_code), format2)
            sheet.write(row, 1, str(product.name), format2)
            sheet.write(row, 2, str(product.categ_id.name), format2)
            sheet.write(row, 3, str(product.season), format2)
            
            color=''
            size=''
            inner_count=0
            for attr in product.product_template_variant_value_ids:
                inner_count+=1
                if inner_count==1:
                    color=attr.name
                if inner_count==2:  
                    size=attr.name                    
            sheet.write(row, 4, str(color), format2)
            sheet.write(row, 5, str(size), format2)
            sheet.write(row, 6, str(product.uom_id.name), format2)
            sheet.write(row, 7, str('{0:,}'.format(int(round(product.list_price)))), format2)
            sheet.write(row, 8, str('{0:,}'.format(int(round(product.list_price)))), format2)
            #Opening Stock  
            opening_qunats = quantsa.search([('product_id','=',uniq_product),('in_date','<',docs.date_from),('location_id','in',docs.location_ids.ids)])
            quants = [op_qt.quantity for op_qt in opening_qunats]
            within_quantsa = quantsa.search([('product_id','=',uniq_product),('in_date','>=',docs.date_from),('in_date','<=',docs.date_to),('location_id','in',docs.location_ids.ids)])
            within_quants = [cl_qt.quantity for cl_qt in within_quantsa]
            opening_vals = sum(quants)
            closing_vals = sum(within_quants)
            in_transit_qty = 0
            adjustment_qty = 0
            transfer_out_qty = 0
            sales_qty = 0
            sale_rtn_qty = 0
            transfer_in_qty = 0
            purchase_qty = 0
            aout_stock_move_lines = out_stock_move_lines.search([('product_id','=',uniq_product)])
            ain_stock_move_lines = in_stock_move_lines.search([('product_id','=',uniq_product)])
            for out_line in aout_stock_move_lines:
                #stock in Transit
                if out_line.location_id.id in (913,934,951,952):
                    in_transit_qty += out_line.qty_done
                #Adjustment
                if out_line.location_id.id in (14,15):
                    adjustment_qty += out_line.qty_done
                #Purchases
                if out_line.location_id.id==4:
                    purchase_qty += out_line.qty_done
                #Transfer In
                if out_line.location_id.id!=4 and out_line.location_id.id not in (913,934,951,952,14,15):
                    transfer_in_qty += out_line.qty_done
                #Sales Return
                if out_line.location_id.id==5:
                    sale_rtn_qty += out_line.qty_done
            for in_line in ain_stock_move_lines:
                #Adjustment
                if in_line.location_dest_id.id in (14,15):
                    adjustment_qty += in_line.qty_done
                #Transfer Out
                if in_line.location_dest_id.id!=5 and in_line.location_dest_id.id not in (913,934,951,952,14,15):
                    transfer_out_qty += in_line.qty_done
                #Sales
                if in_line.location_dest_id.id==5:
                    sales_qty += in_line.qty_done
            
            if product.uom_id.id==9:
               in_transit_qty = in_transit_qty * 12 
               adjustment_qty = adjustment_qty * 12 
               purchase_qty = purchase_qty * 12 
               transfer_in_qty = transfer_in_qty * 12 
               sale_rtn_qty = sale_rtn_qty * 12 
               transfer_out_qty = transfer_out_qty * 12 
               sales_qty = sales_qty * 12 
               opening_vals = opening_vals * 12 
               closing_vals = closing_vals * 12 
             
            sheet.write(row, 9,str('{0:,}'.format(int(round(opening_vals)))), format2)
            total_opening_qty += opening_vals
            sheet.write(row, 10, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_opening_list_price += product.standard_price
            sheet.write(row, 11, str('{0:,}'.format(int(round( product.standard_price * opening_vals)))), format2)
            total_opening_amount += (product.standard_price * opening_vals)
            #Purchases
            sheet.write(row, 12, str('{0:,}'.format(int(round(purchase_qty)))), format2)
            total_purchase_qty += purchase_qty
            sheet.write(row, 13, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_purchase_list_price += product.standard_price
            sheet.write(row, 14, str('{0:,}'.format(int(round(product.standard_price * purchase_qty)))), format2)
            total_purchase_amount += product.standard_price * purchase_qty
            #Transfer In
            sheet.write(row, 15, str('{0:,}'.format(int(round(transfer_in_qty)))), format2)
            total_transfer_in_qty += transfer_in_qty
            sheet.write(row, 16, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_transfer_in_list_price += product.standard_price
            sheet.write(row, 17, str('{0:,}'.format(int(round(product.standard_price * transfer_in_qty)))), format2)
            total_transfer_in_amount += product.standard_price * transfer_in_qty
            #Sales Return
            sheet.write(row, 18, str('{0:,}'.format(int(round(sale_rtn_qty)))), format2)
            total_sale_rtn_qty += sale_rtn_qty
            sheet.write(row, 19, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_sale_rtn_list_price += product.standard_price
            sheet.write(row, 20, str('{0:,}'.format(int(round(product.standard_price * sale_rtn_qty)))), format2)
            total_sale_rtn_amount += product.standard_price * sale_rtn_qty
            #Sales
            sheet.write(row, 21, str('{0:,}'.format(int(round(sales_qty)))), format2)
            total_sales_qty += sales_qty
            sheet.write(row, 22, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_sales_list_price += product.standard_price
            sheet.write(row, 23, str('{0:,}'.format(int(round(product.standard_price * sales_qty)))), format2)
            total_sales_amount += product.standard_price * sales_qty
            sheet.write(row, 24, str('{0:,}'.format(int(round(invoice_amount)))), format2)
            total_sales_inv_amount += invoice_amount
            #Transfer Out
            sheet.write(row, 25, str('{0:,}'.format(int(round(transfer_out_qty)))), format2)
            total_transfer_out_qty += transfer_out_qty
            sheet.write(row, 26, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_transfer_out_list_price += product.standard_price
            sheet.write(row, 27, str('{0:,}'.format(int(round(product.standard_price * transfer_out_qty)))), format2)
            total_transfer_out_amount += product.standard_price * transfer_out_qty
            #Adjustment
            sheet.write(row, 28, str('{0:,}'.format(int(round(adjustment_qty)))), format2)
            total_adjustment_qty += adjustment_qty
            sheet.write(row, 29, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_adjustment_list_price += product.standard_price
            sheet.write(row, 30, str('{0:,}'.format(int(round(product.standard_price * adjustment_qty)))), format2)
            total_adjustment_amount += product.standard_price * adjustment_qty
            #Closing Stock
            sheet.write(row, 31, str('{0:,}'.format(int(round(closing_vals)))), format2)
            total_closing_qty += closing_vals
            sheet.write(row, 32, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_closing_list_price += product.standard_price
            sheet.write(row, 33, str('{0:,}'.format(int(round(product.standard_price * closing_vals)))), format2)
            total_closing_amount += product.standard_price * closing_vals
            #stock in Transit            
            sheet.write(row, 34, str('{0:,}'.format(int(round(in_transit_qty)))), format2)
            total_in_transit_qty += in_transit_qty
            sheet.write(row, 35, str('{0:,}'.format(int(round(product.standard_price)))), format2)
            total_in_transit_list_price += product.standard_price
            sheet.write(row, 36, str('{0:,}'.format(int(round(product.standard_price * in_transit_qty)))), format2)
            total_in_transit_amount += product.standard_price * in_transit_qty
            row+=1
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
        sheet.write(row, 9,str('{0:,}'.format(int(round(total_opening_qty)))), header_row_style)
        sheet.write(row, 10, str('{0:,}'.format(int(round(total_opening_list_price)))), header_row_style)
        sheet.write(row, 11, str('{0:,}'.format(int(round(total_opening_amount)))), header_row_style)
        #Purchases
        sheet.write(row, 12, str('{0:,}'.format(int(round(total_purchase_qty)))), header_row_style)
        sheet.write(row, 13, str('{0:,}'.format(int(round(total_purchase_list_price)))), header_row_style)
        sheet.write(row, 14, str('{0:,}'.format(int(round(total_purchase_amount)))), header_row_style)
        #Transfer In
        sheet.write(row, 15, str('{0:,}'.format(int(round(total_transfer_in_qty)))), header_row_style)
        sheet.write(row, 16, str('{0:,}'.format(int(round(total_transfer_in_list_price)))), header_row_style)
        sheet.write(row, 17, str('{0:,}'.format(int(round(total_transfer_in_amount)))), header_row_style)
        #Sales Return
        sheet.write(row, 18, str('{0:,}'.format(int(round(total_sale_rtn_qty)))), header_row_style)
        sheet.write(row, 19, str('{0:,}'.format(int(round(total_sale_rtn_list_price)))), header_row_style)
        sheet.write(row, 20, str('{0:,}'.format(int(round(total_sale_rtn_amount)))), header_row_style)
        #Sales
        sheet.write(row, 21, str('{0:,}'.format(int(round(total_sales_qty)))), header_row_style)
        sheet.write(row, 22, str('{0:,}'.format(int(round(total_sales_list_price)))), header_row_style)
        sheet.write(row, 23, str('{0:,}'.format(int(round(total_sales_amount)))), header_row_style)
        sheet.write(row, 24, str('{0:,}'.format(int(round(total_sales_inv_amount)))), header_row_style)
        #Transfer Out
        sheet.write(row, 25, str('{0:,}'.format(int(round(total_transfer_out_qty)))), header_row_style)
        sheet.write(row, 26, str('{0:,}'.format(int(round(total_transfer_out_list_price)))), header_row_style)
        sheet.write(row, 27, str('{0:,}'.format(int(round(total_transfer_out_amount)))), header_row_style)
        #Adjustment
        sheet.write(row, 28, str('{0:,}'.format(int(round(total_adjustment_qty)))), header_row_style)
        sheet.write(row, 29, str('{0:,}'.format(int(round(total_adjustment_list_price)))), header_row_style)
        sheet.write(row, 30, str('{0:,}'.format(int(round(total_adjustment_amount)))), header_row_style)
        #Closing Stock
        sheet.write(row, 31, str('{0:,}'.format(int(round(total_closing_qty)))), header_row_style)
        sheet.write(row, 32, str('{0:,}'.format(int(round(total_closing_list_price)))), header_row_style)
        sheet.write(row, 33, str('{0:,}'.format(int(round(total_closing_amount)))), header_row_style)
        #stock in Transit
        sheet.write(row, 34, str('{0:,}'.format(int(round(total_in_transit_qty)))), header_row_style)
        sheet.write(row, 35, str('{0:,}'.format(int(round(total_in_transit_list_price)))), header_row_style)
        sheet.write(row, 36, str('{0:,}'.format(int(round(total_in_transit_amount)))), header_row_style)        
