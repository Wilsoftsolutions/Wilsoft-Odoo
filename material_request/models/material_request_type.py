# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class PickingType(models.Model):
	_inherit = "stock.picking.type"

	def get_new_internal_transfer(self):
		return self._get_action('material_request.action_new_transfer_internal')

	@api.model
	def write_internal_type(self):
		picking_type_ids = self.env['stock.picking.type']
		picking_type_ids = self.search([('name', '=', 'Internal Transfers'), ('active', '=', False)])
		if not picking_type_ids:
			picking_type_ids = self.search([('code', '=', 'internal'), ('active', '=', False)])
		picking_type_ids.write({'active': True})
