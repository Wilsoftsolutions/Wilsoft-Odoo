# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(InheritStockPicking, self).button_validate()
        if self.name.split('/')[1].upper() == 'RET':
            self.sale_id._create_invoices(final=True)
        return res
