# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseInherit(models.Model):
	_inherit = 'purchase.order'

	@api.onchange('order_line')
	def onchange_method(self):
		for rec in self:
			for i in rec.order_line:
				i.taxes_id = rec.partner_id.purchase_tax_ids
