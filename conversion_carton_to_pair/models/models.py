# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class convertion_carton_to_pair(models.Model):
#     _name = 'convertion_carton_to_pair.convertion_carton_to_pair'
#     _description = 'convertion_carton_to_pair.convertion_carton_to_pair'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
