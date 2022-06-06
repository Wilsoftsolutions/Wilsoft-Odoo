# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class QcInspection(models.Model):
    _name = 'qc.inspection'
    _description = 'Qc Inspection'
    
    
    name = fields.Many2one('hr.employee',string='Quality Control Inspector',domain="[('job_id', '=', 'Officer QA')]")
    ref=fields.Char(string='Ref. SR# :')
    vendor_id=fields.Many2one('res.partner',string='Vendor Name',domain="[('category_id', '=', 'Vendor')]")
    purchase_order_id=fields.Many2one('purchase.order',string='Purchase Order',domain="[('invoice_status', '=', 'no'),('partner_id', '=', ' ')]")
    po_item_id=fields.Many2one('purchase.order.line',string='Article',domain="[('order_id', '=', ' ')]")
    article=fields.Char(string=' ',readonly=True)
    color=fields.Char(string=' ',readonly=True)
    image=fields.Char(string=' ',readonly=True)
    plan=fields.Integer(string=' ')
    check39=fields.Integer(string=' ')
    check40=fields.Integer(string=' ')
    check41=fields.Integer(string=' ')
    check42=fields.Integer(string=' ')
    check43=fields.Integer(string=' ')
    check44=fields.Integer(string=' ')
    check45=fields.Integer(string=' ')
    check46=fields.Integer(string=' ')
    rework39=fields.Integer(string=' ')
    rework40=fields.Integer(string=' ')
    rework41=fields.Integer(string=' ')
    rework42=fields.Integer(string=' ')
    rework43=fields.Integer(string=' ')
    rework44=fields.Integer(string=' ')
    rework45=fields.Integer(string=' ')
    rework46=fields.Integer(string=' ')
    bpair39=fields.Integer(string=' ')
    bpair40=fields.Integer(string=' ')
    bpair41=fields.Integer(string=' ')
    bpair42=fields.Integer(string=' ')
    bpair43=fields.Integer(string=' ')
    bpair44=fields.Integer(string=' ')
    bpair45=fields.Integer(string=' ')
    bpair46=fields.Integer(string=' ')
    upper=fields.Char(string='Upper')
    linning=fields.Char(string='Linning')
    mid_sole=fields.Char(string='MID Sole')
    outsole=fields.Char(string='OUTSole')
    finished=fields.Char(string='Finished')
    packaging=fields.Char(string='Packaging')
    acc=fields.Char(string='Acc')
    other=fields.Char(string='Others')
    comment = fields.Text(string="Comment")
    attch_ids = fields.Many2many('ir.attachment', 'ir_attach_rel',  'record_relation_id', 'attachment_id', string="Attachments",
help="If any")
    
    
    @api.onchange('vendor_id')
    def onchange_vendor_id(self):
        self.purchase_order_id=''
        return {'domain': {'purchase_order_id': [('partner_id', '=', self.vendor_id.id)]}}
    @api.onchange('purchase_order_id')
    def onchange_purchase_order_id(self):
        self.po_item_id=''
        return {'domain': {'po_item_id': [('order_id', '=', self.purchase_order_id.id)]}}
    
