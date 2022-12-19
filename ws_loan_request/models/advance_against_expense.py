# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class AdvanceAgainstExpense(models.Model):
    _name = 'advance.against.expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Advance Against Expense"



    name = fields.Char(string="Name", default="/", readonly=True, help="Name of the loan")
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
    approval_request_id = fields.Many2one('hr.approval.request', string="Approval Request")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee",)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 states={'draft': [('readonly', False)]})
    amount = fields.Float(string="Amount", required=True, help="amount")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )
    desciption = fields.Char(string='Reason')
    
    
    
    @api.constrains('amount')
    def _check_amount(self):
        for line in self:            
            if line.employee_id.is_advance_expense==False:
                raise UserError('Not Allow to Request Advance Against Expense! ')
    
    
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('advance.against.seq') or ' '
        res = super(AdvanceAgainstExpense, self).create(values)
        res.action_submit()
        return res
    
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        for line in self:
            servicedata = self.env['category.approval'].sudo().search([('is_advance_against','=',True),('company_id','=',line.employee_id.company_id.id)], limit=1)
            if not servicedata:
                categ_vals = {
                    'name': 'Advance Against Expense',
                    'is_advance_against': True ,
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
                    'name': ' Advance Against Expense '+str(line.amount)+' Date '+str(line.date),
                    'description': ' Advance Against Expense '+str(line.amount)+' Date '+str(line.date),
                    'user_id': line.employee_id.user_id.id,
                    'model_id': 'advance.against.expense',
                    'record_id': line.id,
                    'category_id': servicedata.id,
                    'date': line.date,
                    'company_id': line.employee_id.company_id.id,
                }  
                approval = self.env['hr.approval.request'].sudo().create(approval_vals)
                if line.employee_id.is_hr_approval==True and line.employee_id.company_id.hr_id:
                    approver_vals = {
                        'user_id': line.employee_id.company_id.hr_id.id,
                        'approver_id': approval.id,
                        'user_status': 'new',
                    }
                    approver_line = self.env['hr.approver.line'].sudo().create(approver_vals)  
                else:
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
        self.write({'state': 'waiting_approval_1'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        for data in self:
            vals = {
            'partner_id': data.employee_id.address_home_id.id,            
            'date': data.date,
            'journal_id': self.env['account.journal'].search([('company_id','=',data.employee_id.company_id.id),('name','=','Cash in hand with Cashier')], limit=1).id,
            'amount': data.amount,
            'ref': data.desciption,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            }
            record = self.env['account.payment'].sudo().create(vals)
            data.write({'state': 'approve'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise ValidationError(
                    'You cannot delete a loan which is not in draft or cancelled state')
        return super(HrLoan, self).unlink()
    
    

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    
    is_advance_expense = fields.Boolean(string='Advance Against Expense')
    
    