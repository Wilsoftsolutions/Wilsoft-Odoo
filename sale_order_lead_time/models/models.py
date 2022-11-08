from odoo import api, fields, models
from datetime import datetime, date


class SaleOderModelInherit(models.Model):
    _inherit = 'sale.order'

    approve_date = fields.Date('Approval Date')

    def action_confirm(self):
        self.approve_date = datetime.now().date()
        res = super(SaleOderModelInherit, self).action_confirm()
        return res
