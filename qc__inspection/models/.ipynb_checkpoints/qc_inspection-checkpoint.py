# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class QcInspection(models.Model):
    _name = 'qc.inspection'
    _description = 'Qc Inspection'
    
    
    name = fields.Many2one('hr.employee',string='Quality Control Inspector:',domain="[('job_id', '=', 'Officer QA')]")
    ref=fields.Char(string='Ref. SR# :')
    vendor_id=fields.Many2one('res.partner',string='Vendor Name',domain="[('category_id', '=', 'Vendor')]")
    purchase_order_id=fields.Many2one('purchase.order',string='Purchase Order',domain="[('invoice_status', '=', 'no'),('partner_id', '=', ' ')]")
    po_item_id=fields.Many2one('purchase.order.line',string='Article',domain="[('order_id', '=', ' ')]")
    article=fields.Char(string=' ')
    color=fields.Char(string=' ')
    image=fields.Char(string=' ')
    plan=fields.Char(string=' ')
    check39=fields.Char(string=' ')
    check40=fields.Char(string=' ')
    check41=fields.Char(string=' ')
    check42=fields.Char(string=' ')
    check43=fields.Char(string=' ')
    check44=fields.Char(string=' ')
    check45=fields.Char(string=' ')
    check46=fields.Char(string=' ')
    rework39=fields.Char(string=' ')
    rework40=fields.Char(string=' ')
    rework41=fields.Char(string=' ')
    rework42=fields.Char(string=' ')
    rework43=fields.Char(string=' ')
    rework44=fields.Char(string=' ')
    rework45=fields.Char(string=' ')
    rework46=fields.Char(string=' ')
    bpair39=fields.Char(string=' ')
    bpair40=fields.Char(string=' ')
    bpair41=fields.Char(string=' ')
    bpair42=fields.Char(string=' ')
    bpair43=fields.Char(string=' ')
    bpair44=fields.Char(string=' ')
    bpair45=fields.Char(string=' ')
    bpair46=fields.Char(string=' ')
    
    @api.onchange('vendor_id')
    def onchange_vendor_id(self):
        self.purchase_order_id=''
        return {'domain': {'purchase_order_id': [('partner_id', '=', self.vendor_id.id)]}}
    @api.onchange('purchase_order_id')
    def onchange_purchase_order_id(self):
        self.po_item_id=''
        return {'domain': {'po_item_id': [('order_id', '=', self.purchase_order_id.id)]}}
    
