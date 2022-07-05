# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleInherit(models.Model):
	_inherit = 'sale.order'

	@api.onchange('order_line')
	def onchange_method(self):
		for rec in self:
			for i in rec.order_line:
				if rec.partner_id.sale_tax_ids:
					i.tax_id = rec.partner_id.sale_tax_ids
				