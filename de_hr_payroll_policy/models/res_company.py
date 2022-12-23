# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    retirement_age = fields.Float(string='Retirement Age')
    hr_id = fields.Many2one('hr.employee', string='HR')
