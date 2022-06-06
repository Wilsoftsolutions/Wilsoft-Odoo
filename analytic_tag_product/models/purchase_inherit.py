# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderInherit(models.Model):
	_inherit = 'purchase.order'

	@api.onchange('order_line')
	def onchange_analytic_tag(self):
		for rec in self:
			for i in rec.order_line:
				i.analytic_tag_ids = i.product_id.categ_id.analytic_tag_id

	def button_confirm(self):
		res = super(PurchaseOrderInherit, self).button_confirm()
		for rec in self:
			for i in rec.order_line:
				rec.picking_ids.move_ids_without_package.stock_analytic_tag_id =  i.analytic_tag_ids
		return res



