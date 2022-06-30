from odoo import fields, api, models, _


class UpdateProductQuantity(models.Model):
    _name = 'update.prod'

    vendor_id = fields.Many2one('res.partner', 'Vendor')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase order')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line')
    size36 = fields.Integer('36')
    size37 = fields.Integer('37')
    size38 = fields.Integer('38')
    size39 = fields.Integer('39')
    size40 = fields.Integer('40')
    size41 = fields.Integer('41')
    size42 = fields.Integer('42')
    size43 = fields.Integer('43')
    size44 = fields.Integer('44')
    size45 = fields.Integer('45')
    size46 = fields.Integer('46')
