# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _


class TransactionHistory(models.TransientModel):
    _name = "transaction.history"
    _inherit = ["transaction.history", "portal.mixin"]

