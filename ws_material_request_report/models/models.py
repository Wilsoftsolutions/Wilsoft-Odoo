# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ 


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    is_vendor = fields.Boolean(string='Vendor Location')
    is_customer = fields.Boolean(string='Customer Location')
    is_transit = fields.Boolean(string='Transit Location')
    is_adjustment = fields.Boolean(string='Adjustment Location')
    
    

