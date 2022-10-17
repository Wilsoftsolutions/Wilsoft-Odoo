# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    
    def action_create_plot_inv(self):
        for line in self:
            product_list = []
            for sale_line in line.order_line:
                product_sale_acc = self.env['account.account'].search([('id','=',144)], limit=1)
                if not product_sale_acc:
                    product_sale_acc = self.env['account.account'].search([('user_type_id.name' ,'=', 'Income')], limit=1)  
                product_list.append((0,0, {
                    'name': str(sale_line.product_id.name),
                    'account_id': product_sale_acc.id,
                    'quantity': 1, 
                    'price_unit': sale_line.price_subtotal,
                    'partner_id': line.partner_id.id,
                }))
            # Other Income 
            other_inc_acc = self.env['account.account'].search([('id','=',454)], limit=1)
            if not other_inc_acc:
                other_inc_acc = self.env['account.account'].search([('user_type_id.name' ,'=', 'Other Income')], limit=1)
            if sale_line.processing_fee > 0:
                product_list.append((0,0, {
                    'name': 'Plot '+ str(sale_line.product_id.name) +' Processing Fee',
                    'account_id': other_inc_acc.id,
                    'quantity': 1, 
                    'price_unit': sale_line.processing_fee,
                    'partner_id': line.partner_id.id,
                }))
            if sale_line.membership_fee > 0:
                product_list.append((0,0, {
                    'name': 'Plot '+ str(sale_line.product_id.name) +' Membership Fee',
                    'account_id': other_inc_acc.id,
                    'quantity': 1, 
                    'price_unit': sale_line.membership_fee,
                    'partner_id': line.partner_id.id,
                }))
            journal = self.env['account.journal'].search([('id','=', 25)], limit=1) 
            if not journal:
                journal = self.env['account.journal'].search([('type','=', 'sale')], limit=1)               
            vals = {
                'partner_id': line.partner_id.id,
                'journal_id': journal.id,
                'invoice_date': fields.Date.today(),
                'move_type': 'out_invoice',
                'state': 'draft',
                'invoice_origin': line.name,
                'invoice_line_ids': product_list   
                }
            move = self.env['account.move'].create(vals)