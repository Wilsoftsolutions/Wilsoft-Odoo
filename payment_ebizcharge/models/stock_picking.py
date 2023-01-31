# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class StockPicking(models.Model):

    _inherit = ['stock.picking', 'ebiz.charge.api']
    _name = 'stock.picking'

    ebiz_refund_refnum = fields.Char(default=False)
    show_ebiz_return = fields.Boolean(compute="_compute_ebiz_return")

    def _compute_ebiz_return(self):
        if "Return" in self.origin and bool(self.sale_id) and not self.ebiz_refund_refnum:
            self.show_ebiz_return = True
        else:
            self.show_ebiz_return = False

    def process_credit_transaction(self):
        payment_obj = {
            # "invoice_id": self.sale_id.id,
            "partner_id": self.sale_id.partner_id.id,
            "sale_id": self.sale_id.id,
            "picking_id": self.id,
            "currency_id": self.sale_id.currency_id.id,
        }
        wiz = self.env['wizard.process.credit.transaction'].create(payment_obj)
        total = wiz._compute_amount()
        wiz.amount = total['price_total']
        if self.sale_id.amount_total == total['price_total']:
            import pdb
            pdb.set_trace()

        action = self.env.ref('payment_ebizcharge.action_process_credit_transaction').read()[0]
        action['res_id'] = wiz.id
        return action
    
    