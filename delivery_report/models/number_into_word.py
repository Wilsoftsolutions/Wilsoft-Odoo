from odoo import models, fields, api


class AccountMoveInherite(models.Model):
    _inherit = 'stock.picking'

    # @api.multi
    num_words = fields.Char(string="Amount In Words:", compute='_compute_amount_in_words')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    total_amount = fields.Float("Total Amount")

    def _compute_amount_in_words(self):
        for rec in self:
            rec.num_words = str(rec.currency_id.amount_to_text(rec.amount_total)) + ' only'

