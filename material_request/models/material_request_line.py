# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class MaterialRequestLine(models.Model):

	_name = "material.request.line"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Material Request Line"

	def copy_data(self, default=None):
		if default is None:
			default = {}
			default['approved_qty'] = 0.0
		return super(MaterialRequestLine, self).copy_data(default)

	@api.depends('product_id', 'description', 'product_uom_id', 'product_qty')
	def _allow_update_line(self):
		for rec in self:
			if rec.material_id.state in ('approved', 'cancel', 'done'):
				rec.allow_update = False
			else:
				rec.allow_update = True

	note = fields.Text(string='comments')
	product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('qty_available','!=',0)])
	description = fields.Char('Description', size=256)
	product_qty = fields.Float('Requested Qty',digits=dp.get_precision('Product Unit of Measure'))
	approved_qty = fields.Float('Approved Qty',digits=dp.get_precision('Product Unit of Measure'))
	product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
	material_id = fields.Many2one('material.request', 'Material Request',ondelete='cascade', readonly=True)
	allow_update = fields.Boolean(string='Allow Update', compute="_allow_update_line",readonly=True)

	@api.onchange('product_id')
	def onchange_product_id(self):
		if self and self.product_id:
			name = self.product_id.name
			if self.product_id.code:
				name = '[%s] %s' % (name, self.product_id.code)
			self.product_uom_id = self.product_id.uom_id.id
			self.product_qty = 1
			self.description = name
