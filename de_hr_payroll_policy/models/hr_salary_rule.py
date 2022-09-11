# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HRSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    
    detail_report = fields.Boolean(string='Detail Report')
    detail_label = fields.Char(string='Detail Label')
    detail_deduction = fields.Boolean(string='Detail Deduction')
    detail_compansation = fields.Boolean(string='Detail Compansation')
    detail_sequence = fields.Integer(string='Detail Sequence')
