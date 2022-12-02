# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import requests
import base64
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class ZacutaDataLine(models.Model):
    _name = 'zacuta.order'
    _description = 'Zacuta Order'
    _rec_name = 'zid'

    zid = fields.Char(string='ZID')
    user_id = fields.Char(string='User ID')
    sheet_id = fields.Char(string='Sheet ID')
    booking_date = fields.Char(string='Booking Date')
    promo = fields.Char(string='Promo')
    status = fields.Char(string='Status')
    remarks = fields.Char(string='Remarks')
    cn_number = fields.Char(string='CN Number')
    shipper_id = fields.Char(string='Shipper ID')
    consignment_name = fields.Char(string='Consignment Name')
    consignee_email = fields.Char(string='Consignee Email')
    consignment_addres = fields.Char(string='Consignment Address')
    consignment_phone_number = fields.Char(string='Consignment Phone')
    designation = fields.Char(string='Designation')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('post', 'Posted'),
        ('cancel', 'Cancelled'),], string="Status", default="draft")
    order_id = fields.Char(string='Order')
    tracking_number = fields.Char(string='Tracking No')
    cod_amount = fields.Char(string='COD Amount')
    tax = fields.Char(string='Tax')
    comment = fields.Char(string='Comment')
    assigned_to = fields.Char(string='Assigned To')
    rts = fields.Char(string='Rts')
    weight = fields.Char(string='Weight')
    delivery_price = fields.Char(string='Delivery Price')
    discount = fields.Char(string='Discount')
    advance = fields.Char(string='Advance')
    added_by = fields.Char(string='Added By')
    last_edit_by = fields.Char(string='Last Edit By')
    created_at = fields.Char(string='Created At')
    updated_at = fields.Char(string='Updated At')
    deposit_type = fields.Char(string='Deposit Type')
    deposit_status = fields.Char(string='Deposit Status')
    deposit_accept_date = fields.Char(string='Deposit Accept Date')
    bank_trans_details = fields.Char(string='Bank Trans Details')
    reminder_comments = fields.Char(string='Reminder Comments')
    reminder_date = fields.Char(string='Reminder Date')
    reminder = fields.Char(string='Reminder')
    reminder_flag = fields.Char(string='Reminder Flag')
    source = fields.Char(string='Source')
    shopify_order_id = fields.Char(string='Shopify Order')
    shipper_tracking_id = fields.Char(string='Shipper Tracking')
    return_remarks = fields.Char(string='Return Remarks')
    attempt = fields.Char(string='Attempt')
    shipper_last_status = fields.Char(string='Shipper last Status')
    shipper_shipping_stats = fields.Char(string='Shipper Shipping Stats')
    booking_complete_status = fields.Char(string='Booking Complete Status')
    fetched = fields.Char(string='Fetched')
    shipper_slip_link = fields.Char(string='shipper Slip link')
    province = fields.Char(string='Province')
    commission = fields.Char(string='Commission')
    order_line = fields.One2many('zacuta.order.line', 'order_id', string='Order Lines')
    pay_line = fields.One2many('zacuta.pay.line', 'order_id', string='Payment Lines')
    shipper_line_ids = fields.One2many('zacuta.shipper.line', 'order_id', string='Shipper Lines')
    rider_line_ids = fields.One2many('zacuta.rider.line', 'order_id', string='Rider Line')
    
 
class RiderLine(models.Model):
    _name ='zacuta.rider.line'
    _description= 'Zacuta Rider Line'
    
    id  = fields.Char(string='ID')
    name = fields.Char(string='Name')
    username = fields.Char(string='Username')
    password = fields.Char(string='Password')
    token = fields.Char(string='Token')
    phone = fields.Char(string='Phone')
    address = fields.Char(string='Address')
    delete_status = fields.Char(string='Delete Status')
    status = fields.Char(string='Status')
    created_at = fields.Char(string='Created At')
    updated_at = fields.Char(string='Update At') 
    order_id = fields.Many2one('zacuta.order', string='Order')
    
    
class ShipperLine(models.Model):
    _name ='zacuta.shipper.line'
    _description= 'Zacuta Shipper Line'
    
    id  = fields.Char(string='ID')
    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    phone_number = fields.Char(string='Phone No')
    address = fields.Char(string='Address')
    origin_city = fields.Char(string='Origin City')
    created_at = fields.Char(string='Created At')
    updated_at = fields.Char(string='Update At')
    api_status = fields.Char(string='API Status')
    order_id = fields.Many2one('zacuta.order', string='Order')
    
    
class ZacutaOrderLine(models.Model):
    _name ='zacuta.order.line'
    _description= 'Zacuta Order Line'
    
    name  = fields.Char(string='Name')
    quantity = fields.Float(string='Quantity')
    price = fields.Float(string='Price')
    order_id = fields.Many2one('zacuta.order', string='Order')

    
    
class ZacutaPayLine(models.Model):
    _name ='zacuta.pay.line'
    _description= 'Zacuta Pay Line'
    
    cn_number  = fields.Char(string='CN Number')
    billing_method = fields.Float(string='Billing Method')
    invoice_cheque_no = fields.Float(string='Invoice Cheque No')    
    invoice_cheque_date = fields.Char(string='Invoice Cheque Date')
    weight_charged = fields.Char(string='Weight Charged')
    shipment_charges = fields.Char(string='Shipment Charge')
    cash_handling_charges = fields.Char(string='Cash Handling Charge')
    return_charges = fields.Char(string='Return Charge')
    insurance_charges = fields.Char(string='Insurance Charge')
    fuel_surcharge_percentage = fields.Char(string='Fuel Surcharge Percent')
    fuel_surcharge_amount = fields.Char(string='Fuel Surcharge Amount')
    gst = fields.Char(string='GST')
    gst_amount = fields.Char(string='GST Amount')
    net_charges = fields.Char(string='Net Charge')
    gross_charges = fields.Char(string='Gross Charges')
    order_id = fields.Many2one('zacuta.order', string='Order')
