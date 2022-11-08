# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplateInherit(models.Model):
    _inherit = 'product.product'
    _description = 'product.product'

    season = fields.Char('Season')
