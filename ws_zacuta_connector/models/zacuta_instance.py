# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import requests
import base64
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class ZacutaConnector(models.Model):
    _name = 'zacuta.instance'
    _description = 'Zacuta Instance'

    
    name = fields.Char(string='Name')
    url = fields.Char(string='URL')
    token = fields.Char(string='Token')
    journal_id = fields.Many2one('account.journal', string='Payment Journal')
    je_journal_id = fields.Many2one('account.journal', string='JV Journal')
    debit_account = fields.Many2one('account.account', string='Debit Account')
    credit_account = fields.Many2one('account.account', string='Credit Account')
    delivery_charges = fields.Float(string='Delivery Charges')
    weigh_charges = fields.Float(string='Weight Charges')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('close', 'Closed'),], string="Status",
                             default="draft")
    
    
    
    def action_fetch_data(self):
        header = {'Accept': 'application/json', "Content-Type": "application/json"}
        zacuta_instance = self.env['zacuta.instance'].search([], limit=1)
        header.update({'ApiToken': str(zacuta_instance.token)})
        url = str(zacuta_instance.url)
        req = requests.request('POST', url, headers=header)
        data_list = req.content
        final_list = json.loads(data_list)
        inner_count = 0
        invoices = self.env['account.move'].search([('payment_state','=','not_paid'),('ref','!=',' '),('invoice_date','>=','2022-12-01'),('state','=','posted')])
        for inv in invoices:
            for data in final_list['bookings']:
                if data['status'] in ('DELIVERED','Delivered') and inv.ref==data['order_id']:
                    vals = {
                       'zid': data['id'],
                       'user_id': data['user_id'],
                       'sheet_id': data['sheet_id'],
                       'booking_date': data['booking_date'],
                        'promo': data['promo'],
                       'status': data['status'],
                       'remarks': data['remarks'],
                        'cn_number': data['cn_number'],
                       'shipper_id': data['shipper_id'],
                       'consignment_name': data['consignment_name'],
                        'consignee_email': data['consignee_email'],
                       'consignment_addres': data['consignment_addres'],
                       'consignment_phone_number': data['consignment_phone_number'],
                       'designation': data['designation'],
                        'order_id': data['order_id'],
                       'tracking_number': data['tracking_number'],
                       'cod_amount': data['cod_amount'],
                        'tax': data['tax'],
                       'comment': data['comment'],
                       'assigned_to': data['assigned_to'],
                        'rts': data['rts'],
                       'weight': data['weight'],
                       'delivery_price': data['delivery_price'],
                       'discount': data['discount'],
                        'advance': data['advance'],
                       'added_by': data['added_by'],
                       'last_edit_by': data['last_edit_by'],
                        'created_at': data['created_at'],
                       'updated_at': data['updated_at'],
                       'deposit_type': data['deposit_type'],
                        'deposit_status': data['deposit_status'],
                       'deposit_accept_date': data['deposit_accept_date'],
                       'bank_trans_details': data['bank_trans_details'],
                       'reminder_comments': data['reminder_comments'],
                        'reminder_date': data['reminder_date'],
                       'reminder': data['reminder'],
                       'reminder_flag': data['reminder_flag'],
                        'source': data['source'],
                       'shopify_order_id': data['shopify_order_id'],
                       'shipper_tracking_id': data['shipper_tracking_id'],
                        'return_remarks': data['return_remarks'],
                       'attempt': data['attempt'],
                       'shipper_last_status': data['shipper_last_status'],
                       'shipper_shipping_stats': data['shipper_shipping_stats'],
                        'booking_complete_status': data['booking_complete_status'],
                       'fetched': data['fetched'],
                       'shipper_slip_link': data['shipper_slip_link'],
                        'province': data['province'],
                       'commission': data['commission'],
                    }
                    order = self.env['zacuta.order'].create(vals)
                    for product in json.loads(data['products']):
                        product_vals = {
                            'name': product['name'],
                            'quantity': product['quantity'],
                            'price': product['price'],
                            'order_id': order.id,
                        }
                        order_line = self.env['zacuta.order.line'].create(product_vals)

                    shipper_list = []
                    shipper_list.append(data['shipper'])
                    shippera = ''
                    if shipper_list and data['shipper']!=None:
                        
                        for shipper in shipper_list:
                            shippera=shipper['name']
                            shipper_vals = {
                                'id': shipper['id'],
                                'name': shipper['name'],
                                'email': shipper['email'],
                                'phone_number': shipper['phone_number'],
                                'address': shipper['address'],
                                'origin_city': shipper['origin_city'],
                                'created_at': shipper['created_at'],
                                'updated_at': shipper['updated_at'],
                                'api_status': shipper['api_status'],
                                'order_id': order.id,
                            }
                            shipper_line = self.env['zacuta.shipper.line'].create(shipper_vals)  
                    rider_list = []
                    rider_list.append(data['rider'])
                    if rider_list and data['rider']!=None:
                        for rider in rider_list:
                            rider_vals = {
                                'id': rider['id'],
                                'name': rider['name'],
                                'username': rider['username'],
                                'password': rider['password'],
                                'token': rider['token'],
                                'phone': rider['phone'],
                                'address': rider['address'],
                                'delete_status': rider['delete_status'],
                                'status': rider['status'],
                                'created_at': rider['created_at'],
                                'updated_at': rider['updated_at'],
                                'order_id': order.id,
                            }
                            rider_line = self.env['zacuta.rider.line'].create(rider_vals)   
                    order.update({
                       'state': 'post',
                    })   
                    predebit= self.delivery_charges
                    if float(order.weight)>1:
                        predebit = float(self.delivery_charges) + ((float(order.weight)-1) * float(self.weigh_charges))   
                    precredit=predebit
                    order = order.zid 
                    invoicea = inv.name
                    qty = data['weight']
                    self.action_post_commission_jv(predebit, precredit, order, invoicea, qty, shippera)
                    if float(data['cod_amount']) > 0: 
                        vals = {
                            'journal_id': self.journal_id.id,
                            'payment_type': 'inbound',
                            'date': data['booking_date'],
                            'amount': float(data['cod_amount']),
                        }  
                        payment = self.env['account.payment'].create(vals)
                        payment.action_post()
                        inv_line=0
                        for je_line in inv.line_ids:
                            if je_line.debit!=0:
                                inv_line=self.env['account.move.line'].search([('move_id','=',je_line.move_id.id),('debit','!=',0)])    
                        credit_line=0
                        for payline in payment.line_ids:
                            if payline.credit!=0:
                                credit_line=self.env['account.move.line'].search([('move_id','=',payline.move_id.id),('credit','!=',0)]) 
                        if credit_line:        
                            (credit_line + inv_line)\
                                .filtered_domain([('account_id', '=', credit_line.account_id.id), ('reconciled', '=', False)])\
                                .reconcile()
                        
                        
                        
    def action_post_commission_jv(self, debit, credit, order, invoicea, qty, shippera):
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        if self.je_journal_id and self.debit_account and self.credit_account:
            move_vals = {
               'date': fields.date.today(),
               'journal_id': self.je_journal_id.id,
                'ref': str(order) +' Invoice# '+ str(invoicea),
            }
            move = self.env['account.move'].create(move_vals)
            debit_line = (0, 0, {
                   'name': 'Quantity '+str(qty)+' Zacuta Commission on'+str(fields.date.today()),
                    'account_id': self.debit_account.id,
                    'journal_id': self.je_journal_id.id,
                    'date': fields.date.today(),
                    'debit': debit,
                    'credit': 0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                   'name': 'Shipper: '+str(shippera)+' Zacuta Commission '+str(fields.date.today()),
                    'account_id': self.credit_account.id,
                    'journal_id': self.je_journal_id.id,
                    'date': fields.date.today(),
                    'debit': 0,
                    'credit': credit,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move['line_ids'] = line_ids 
            move.action_post()

    
    def action_check_connection(self):
        for line in self:
            header = {'Accept': 'application/json', "Content-Type": "application/json"}
            header.update({'ApiToken': str(line.token)})
            url = str(line.url)
            req = requests.request('POST', url, headers=header)
            data_list = req.content
            final_list = json.loads(data_list)
            if final_list['status']=='200':
                raise UserError('Successfully connected to Zacuta Instance!')
            
            

        
        
        
        
        
        
        
        
          # for pay in json.loads(data['shipper_shipping_stats']):
                #     pay_vals = {
                #         'cn_number': pay['cn_number'],
                #         'billing_method': pay['billing_method'],
                #         'invoice_cheque_no': pay['invoice_cheque_no'],
                #         'invoice_cheque_date': pay['invoice_cheque_date'],
                #         'weight_charged': pay['weight_charged'],
                #         'shipment_charges': pay['shipment_charges'],
                #         'cash_handling_charges': pay['cash_handling_charges'],
                #         'return_charges': pay['return_charges'],
                #         'insurance_charges': pay['insurance_charges'],
                #         'fuel_surcharge_percentage': pay['fuel_surcharge_percentage'],
                #         'fuel_surcharge_amount': pay['fuel_surcharge_amount'],
                #         'gst': pay['gst'],
                #         'gst_amount': pay['gst_amount'],
                #         'net_charges': pay['net_charges'],
                #         'gross_charges': pay['gross_charges'],
                #         'order_id': order.id,
                #     }
                #     pay_line = self.env['zacuta.pay.line'].create(pay_vals) \