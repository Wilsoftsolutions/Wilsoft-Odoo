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
    #open stock
    op_qty = fields.Float(string='QTY(Opening)') 
    retail_price = fields.Float(string='Cost Price(Opening)')
    list_price = fields.Float(string='Amount(Opening)')
    #purhcases
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Transfer IN
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Sales Return
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Sales
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    #Transfer Out
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Adjustment
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Closing Stock
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
    #Stock In Transit
    retail_price = fields.Float(string='Retail Price') 
    retail_price = fields.Float(string='Retail Price')
    list_price = fields.Float(string='Wholesale Price')
