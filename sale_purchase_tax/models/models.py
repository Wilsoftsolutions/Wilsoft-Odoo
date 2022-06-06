# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerInherit(models.Model):
	_inherit = 'res.partner'

	sale_tax_ids = fields.Many2many('account.tax','account_tax_relations', 'account_taxs_id', 'account_cr_id',
	    string='Sale Tax')

	purchase_tax_ids = fields.Many2many('account.tax', 'accounts_purchase_relations', 'accounts_purc_id',
									string='Purchase Tax')




