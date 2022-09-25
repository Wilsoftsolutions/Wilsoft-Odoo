# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_is_zero


class PosMakePaymentInherit(models.TransientModel):
    _inherit = 'pos.make.payment'
    _description = 'Point of Sale Make Payment Wizard'


    def check(self):
        rec = super(PosMakePaymentInherit, self).check()
        
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            order.post_data_to_fbr([order.id])
            
        return rec
    