# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HRSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    
    
    rule_type_id = fields.Many2one('rule.parent.type', string='Rule Type')
    
    
class RuleParentType(models.Model):
    _name = 'rule.parent.type'
    _description = 'Rule Parent Type'
    
    name = fields.Char(string='Name', required=True) 
    detail_report = fields.Boolean(string='Detail Report')
    detail_label = fields.Char(string='Detail Label')
    detail_deduction = fields.Boolean(string='Detail Deduction')
    detail_compansation = fields.Boolean(string='Detail Compansation')
    detail_sequence = fields.Integer(string='Detail Sequence')
    sequence = fields.Integer(string='Sequence', required=True)
    
