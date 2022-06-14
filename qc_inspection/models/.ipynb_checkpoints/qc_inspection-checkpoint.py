# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class QcInspection(models.Model):
    _name = 'qc.inspection'
    _description = 'Qc Inspection'
    
    name = fields.Many2one('hr.employee',string='Quality Control Inspector',domain="[('job_id', '=', 'Officer QA')]")
    ref=fields.Char(string='Ref. SR# :',readonly='True')
    vendor_id=fields.Many2one('res.partner',string='Vendor Name',domain="[('category_id', '=', 'Vendor')]")
    purchase_order_id=fields.Many2one('purchase.order',string='Purchase Order',domain="[('invoice_status', '=', 'no'),('partner_id', '=', ' ')]")
    po_item_id=fields.Many2one('purchase.order.line',string='Article',domain="[('order_id', '=', ' ')]")
    image=fields.Char(string=' ' ,readonly='True')
    plan=fields.Integer(string=' ' ,readonly='True')
    status=fields.Char(string=' ', default='Created',readonly='True')
    article39=fields.Integer(string=' ' ,readonly='True')
    article40=fields.Integer(string=' ' ,readonly='True')
    article41=fields.Integer(string=' ' ,readonly='True')
    article42=fields.Integer(string=' ' ,readonly='True')
    article43=fields.Integer(string=' ' ,readonly='True')
    article44=fields.Integer(string=' ' ,readonly='True')
    article45=fields.Integer(string=' ' ,readonly='True')
    article46=fields.Integer(string=' ' ,readonly='True')
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
    @api.onchange('po_item_id')
    def onchange_member_type(self):
        if self.po_item_id:
            self.plan = self.po_item_id.product_qty*12
            #self.article40=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_qty
            for line in self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids:
                self.article39 = line.env['sh.product.bundle'].search([('sh_bundle_id', '=', 2)]).sh_qty
#                 self.article39=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article40=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article41=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article42=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article43=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article44=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article45=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#                 self.article46=self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_bundle_id.sh_qty
#     @api.onchange('po_item_id')
#     def onchange_member_type(self):
#         list_data=[]
#         if self.po_item_id:
#             list_data = self.po_item_id.product_id.product_tmpl_id.sh_bundle_product_ids.sh_qty
#             print("list_data")

    def action_status(self):
        self.status='Confrimed'

