# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero, float_repr
from odoo.tools.misc import clean_context, format_date
from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION



class HrExpense(models.Model):
    _inherit = 'hr.expense'

    location = fields.Char(string='Location')
    loc_from =  fields.Char(string='Location From')
    loc_to  = fields.Char(string='Location To')


class ProductProduct(models.Model):
    _inherit = 'product.product'
        
    employee_type_id = fields.Many2one('emp.type.category',  string='Employee Category'  )


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    approval_request_id = fields.Many2one('hr.approval.request', string='Approval')
    
    
    
    def action_submit_request(self):
        for line in self:
            servicedata = self.env['category.approval'].sudo().search([('name','=','Expense'),('company_id','=',line.employee_id.company_id.id)], limit=1)
            if not servicedata:
                categ_vals = {
                    'name': 'Expense',
                    'company_id':  line.employee_id.company_id.id,
                }
                categ = self.env['category.approval'].sudo().create(categ_vals)
                approver_line  = {
                    'category_id' : categ.id,
                    'user_type': 'hod',
                }
                approver_line = self.env['hr.category.approvers'].sudo().create(approver_line)
                servicedata = categ

            if servicedata.approver_ids:
                approval_vals = {
                    'name': ' Expense '+str(line.total_amount)+' Date '+str(line.accounting_date),
                    'description': ' Expense '+str(line.total_amount)+' Date '+str(line.accounting_date),
                    'user_id': line.employee_id.user_id.id,
                    'model_id': 'hr.expense.sheet',
                    'record_id': line.id,
                    'category_id': servicedata.id,
                    'date': line.accounting_date,
                    'company_id': line.employee_id.company_id.id,
                }  
                approval = self.env['hr.approval.request'].sudo().create(approval_vals)
                for approver in servicedata.approver_ids:
                    user = approver.user_id.id
                    if approver.user_type=='manager':
                        user = line.employee_id.parent_id.user_id.id 
                    if approver.user_type=='hod':
                        user = line.employee_id.department_id.manager_id.user_id.id     
                    approver_vals = {
                        'user_id': user,
                        'approver_id': approval.id,
                        'user_status': 'new',
                    }
                    approver_line = self.env['hr.approver.line'].sudo().create(approver_vals)
                approval.action_submit()
                line.update({
                    'approval_request_id': approval.id,
                })
            line.action_submit_sheet()
   