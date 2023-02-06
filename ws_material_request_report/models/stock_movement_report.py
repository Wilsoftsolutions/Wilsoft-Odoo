# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMovementReport(models.Model):
    _name = 'stock.movement.report'
    _description = 'Stock Movement Report'
    
    
    default_code = fields.Char(string='Item Code')
    name = fields.Char(string='Name')
    categ_id = fields.Char(string='Category')
    season = fields.Char(string='Season')
    size = fields.Char(string='Size')
    color = fields.Char(string='Color')
    uom = fields.Char(string='UOM')
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Source Location')
    location_dest_id = fields.Many2one(, string='Destination Location')
    #open stock
    op_qty = fields.Float(string='QTY(Opening)') 
    op_retail_price = fields.Float(string='Cost Price')
    op_list_price = fields.Float(string='Amount')
    #purhcases
    po_qty = fields.Float(string='QTY(Purchase)') 
    po_retail_price = fields.Float(string='Cost Price')
    po_list_price = fields.Float(string='Amount')
    #Transfer IN
    in_qty = fields.Float(string='QTY(In)') 
    in_retail_price = fields.Float(string='Cost Price')
    in_list_price = fields.Float(string='Amount')
    #Sales Return
    rtn_qty = fields.Float(string='QTY(RTN)') 
    rtn_retail_price = fields.Float(string='Cost Price')
    rtn_list_price = fields.Float(string='Amount')
    #Sales
    so_qty = fields.Float(string='QTY(Sale)') 
    so_retail_price = fields.Float(string='Cost Price')
    so_list_price = fields.Float(string='Amount')
    so_net_amount = fields.Float(string='Net Sale Amount') 
    #Transfer Out
    out_qty = fields.Float(string='QTY(Out)') 
    out_retail_price = fields.Float(string='Cost Price')
    out_list_price = fields.Float(string='Amount')
    #Adjustment
    adj_qty = fields.Float(string='QTY(ADJ)') 
    adj_retail_price = fields.Float(string='Cost Price')
    adj_list_price = fields.Float(string='Amount')
    #Closing Stock
    clsing_qty = fields.Float(string='QTY(Closing)') 
    clsing_retail_price = fields.Float(string='Cost Price')
    clsing_list_price = fields.Float(string='Amount')
    #Stock In Transit
    transit_qty = fields.Float(string='QTY(Transit)') 
    transit_retail_price = fields.Float(string='Cost Price')
    transit_list_price = fields.Float(string='Amount')
