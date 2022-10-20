from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ConversionCartonToPair(models.TransientModel):
    _name = 'conversion.carton.pair'
    _description = 'Description'

    source_id = fields.Many2one('stock.location', string='Source Location',  required=True,)
    location_id = fields.Many2one('stock.location', string='Destination Location',  required=True,)
    product_id = fields.Many2one('product.product', string='Product')
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type',  required=True,)
    quantity = fields.Float(string="Quantity", default=1)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.user.company_id)
    dest_company_id = fields.Many2one('res.company', string='Destination Company')

    def convert_carton_to_pair(self):
        out_picking_value = {}
        in_picking_value = {}
        # out_picking_type_id = self._get_picking_type('outgoing', self.company_id.id)
        # in_picking_type_id = self._get_picking_type('incoming', self.dest_company_id.id)
        Products = self.env['product.product'].search([('id', '=', self.product_id.id)], limit=1)
        out_move_lines = []
        for i in Products.sh_bundle_product_ids:
            out_move_lines.append((0, 0, {
                'product_id': i.sh_product_id.id,
                'product_uom': i.sh_uom.id,
                'product_uom_qty': i.sh_qty * self.quantity,
                'name': i.sh_product_id.name,
                'company_id': self.company_id.id,
                'location_id': self.location_id.id,
                'location_dest_id':self.source_id.id,
            }))
        out_picking_value.update({
            # 'partner_id': 4188,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.source_id.id,
            'move_lines': out_move_lines,
        })
        self.env['stock.picking'].create(out_picking_value)
        in_move_lines = []
        in_move_lines.append((0, 0, {
            'product_id': Products.id,
            'product_uom': Products.uom_id.id,
            'product_uom_qty': self.quantity,
            'name': Products.name,
            'company_id': self.company_id.id,
            'location_id': self.source_id.id,
            'location_dest_id': self.location_id.id,
        }))
        in_picking_value.update({
            # 'partner_id': 4188,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.source_id.id,
            'location_dest_id': self.location_id.id,
            'move_lines': in_move_lines,
        })

        self.env['stock.picking'].create(in_picking_value)
