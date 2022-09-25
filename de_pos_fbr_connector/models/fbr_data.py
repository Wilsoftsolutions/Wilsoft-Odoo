# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import requests
import json
import datetime
import traceback
from datetime import datetime
from lxml.doctestcompare import strip
from odoo.exceptions import UserError


class ReturnDataFBR(models.Model):
    _name = 'pos.order.fbr.log'

    fbr_order_no = fields.Char("Order No.", required=True)
    fbr_invoice_no = fields.Char("Invoice No.")
    fbr_json_data = fields.Char("Json")
    actual_order_id = fields.Many2one('pos.order', string="Receipt No.")
    fbr_response = fields.Char("FBR Response")
    
    _sql_constraints = [
    ('fbr_order_no_uniq', 'unique (fbr_order_no)', "Order No. already exists!"),
    ]
    
    
    @api.model
    def create(self, vals):
        rec = super(ReturnDataFBR, self).create(vals)
        print('----rec',rec.id)
        api_response = rec.post_data_to_fbr(eval(rec.fbr_json_data))
#         rec.fbr_invoice_no = rec.post_data_to_fbr(eval(rec.fbr_json_data))
        rec.fbr_invoice_no = api_response[0]
        rec.fbr_response = api_response[1]
        return rec
    
    def unlink(self):
        raise UserError('Deletion not allowed!')
        rec = super(ReturnDataFBR, self).unlink()
        return rec
    
    
    def post_data_to_fbr(self, pos_order):
        fbr_url = ''
        invoice_number = ''
        r_json = ''
        # Content type must be included in the header
        header = {"Content-Type": "application/json"}
         
        if pos_order:
            print('pos_order----',pos_order)
            try:
                if pos_order.get('post_data_fbr') != True:

                    sale_amount = round(pos_order.get('amount_total') - pos_order.get('amount_tax'), 4)
                    print('sale amount pos validate-------',sale_amount)
                    invoice_type =  ''
                    if sale_amount > 0:
                        invoice_type = 1
                    if sale_amount < 0:
                        invoice_type = 3
                    
#                     statement = pos_order.get('statement_ids')
#                     payment_date = statement[0][2].get('name')
                    print('invoice_type-------',invoice_type)
                    order_dic = {
                        "InvoiceNumber": "",
                        "USIN": pos_order.get('name').partition(' ')[2],
                        "DateTime": pos_order.get('creation_date'), #payment_date, 
                        "TotalBillAmount": abs(round(pos_order.get('amount_total'), 4)),
                        "TotalSaleValue": abs(round(pos_order.get('amount_total') - pos_order.get('amount_tax'), 4)),
                        "TotalTaxCharged": abs(round(pos_order.get('amount_tax'), 4)),
                        "PaymentMode": 1,
                        "InvoiceType": invoice_type,
                    }
                    print('order_dic--000--',order_dic)
                    session = self.env['pos.session'].sudo().search([('id', '=', pos_order.get('pos_session_id'))],limit=1)
                    if session.config_id.enable_fbr:
                        header.update({'Authorization': session.config_id.fbr_authorization})
                        order_dic.update({'POSID': session.config_id.pos_id})
                        fbr_url = session.config_id.fbr_url
    
                    partner = False
                    if pos_order.get('partner_id'):
                        partner = self.env['res.partner'].sudo().search([('id', '=', pos_order.get('partner_id'))],limit=1)
                        order_dic.update({
                            "BuyerName": partner.name,
                            "BuyerPhoneNumber": partner.mobile,
                        })
    
                    if pos_order.get('lines'):
    
                        items_list = []
                        total_qty = 0.0
    
                        for line in pos_order.get('lines'):
                            product_dic = line[2]
                            total_qty += product_dic.get('qty')
                            if 'product_id' in product_dic:
                                product = self.env['product.product'].sudo().search([('id', '=', product_dic.get('product_id'))])
                                if product:
                                    pricelist_id = pos_order.get('pricelist_id')
                                    pricelist = self.env['product.pricelist'].sudo().browse(pricelist_id)
                                    price = float(product_dic.get('price_unit')) * (
                                                   1 - (product_dic.get('discount') or 0.0) / 100.0)
                                    
                                    tax_list = product_dic.get('tax_ids')[0][2]
                                    tax_ids = self.env['account.tax'].sudo().search([('id', 'in', tax_list)])

                                    line_dic = {
                                        "ItemCode": product.barcode,
                                        "ItemName": product.name,
                                        "Quantity": product_dic.get('qty'),
                                        "PCTCode": product.pct_code,
                                        "TaxRate": tax_ids.amount,
                                        "SaleValue": abs(round(product_dic.get('price_subtotal'), 4)),
                                        "TotalAmount": abs(round(product_dic.get('price_subtotal_incl'), 4)),
                                        "TaxCharged": abs(round(product_dic.get('price_subtotal_incl') - product_dic.get('price_subtotal'), 4)),
                                        "InvoiceType": invoice_type,
                                        "RefUSIN": ""
                                    }
                                    items_list.append(line_dic)
                        order_dic.update({'Items': items_list, 'TotalQuantity': abs(total_qty)})
                    print('----order dic',order_dic)
                    print('json.dumps(order_dic)-------',json.dumps(order_dic))
                    payment_response = requests.post(fbr_url, data=json.dumps(order_dic), headers=header, verify=False)
    
                r_json = payment_response.json()
                print('---------r json=======',r_json)
                invoice_number = r_json.get('InvoiceNumber')
                print('==========')
#                 if invoice_number == 'Not Available':
#                     invoice_number = ''
#                 else:
#                     invoice_number = invoice_number
                    
                   
                 
            except Exception as e:
                values = dict(
                    exception=e,
                    traceback=traceback.format_exc(),
                )
 
        return [invoice_number,r_json]
