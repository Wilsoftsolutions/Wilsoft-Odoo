# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductCategoryInherit(models.Model):
	_inherit = 'product.category'

	analytic_tag_id = fields.Many2many('account.analytic.tag', string='Analytic Tag')


class StockMoveInherit(models.Model):
	_inherit = 'stock.move'

	stock_analytic_tag_id = fields.Many2many('account.analytic.tag', 'analytic_tag_stock', 'stock_tags_id', string='Analytic Tag')


# class StockMovelineInherit(models.Model):
# 	_inherit = 'stock.move.line'
#
# 	stock_analytic_tag_ids = fields.Many2many('account.analytic.tag', 'analytic_tags_stock', 'stock_tags_ids', string='Analytic Tag')
# 	test = fields.Char()


class StockPickingInherit(models.Model):
	_inherit = 'stock.picking'

	@api.onchange('move_ids_without_package')
	def onchange_analytic_tagd(self):
		for rec in self:
			for i in rec.move_ids_without_package:
				i.stock_analytic_tag_id = i.product_id.categ_id.analytic_tag_id

	def button_validate(self):
		res = super(StockPickingInherit, self).button_validate()
		for rec in self:
			for i in rec.move_ids_without_package:
				for d in i.account_move_ids:
					d.line_ids.analytic_tag_ids = i.stock_analytic_tag_id
					# i.stock_analytic_tag_id = i.product_id.categ_id.analytic_tag_id



		return res
