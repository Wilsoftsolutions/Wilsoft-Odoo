# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from openerp import models, fields, api, _
from openerp.exceptions import Warning

class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean('Restrict Location')

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations')

    default_picking_type_ids = fields.Many2many(
        'stock.picking.type', 'stock_picking_type_users_rel',
        'user_id', 'picking_type_id', string='Default Warehouse Operations')


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.constrains('state', 'location_id', 'location_dest_id')
    def check_user_location_rights(self):
        for rec in self:
            if rec.state == 'draft':
                return True

            user_locations = rec.env.user.stock_location_ids
            if rec.env.user.restrict_locations:
                message ='Invalid Location. You cannot process this move since you do not control the location Please contact your Adminstrator.'
                if rec.location_id not in user_locations:
                    message ='Invalid Location. You cannot process this move since you do not control the location '+str(rec.location_id.name)+' Please contact your Adminstrator.'
                    raise UserError(str(message))
                elif rec.location_dest_id not in user_locations:
                    message ='Invalid Location. You cannot process this move since you do not control the location '+str(rec.location_dest_id.name)+' Please contact your Adminstrator.'
                    raise UserError(str(message))
