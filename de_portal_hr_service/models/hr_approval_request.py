# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError



class CategoryApproval(models.Model):
    _name = 'category.approval'
    _description = 'Approval Category'
    
    name  = fields.Char(string='Desciption')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_attendance_rectify = fields.Boolean(string='Attendance Rectification')
    is_advance_against = fields.Boolean(string='Advance Against Expense')
    approver_ids = fields.One2many('hr.category.approvers', 'category_id', string='Approvers', copy=True, auto_join=True)
    
    
class HRServiceApprover(models.Model):
    _name = 'hr.category.approvers'
    _description = 'Approvers'
    
    
    category_id = fields.Many2one('category.approval', string='Category', readonly=True)
    user_type = fields.Selection([
        ('manager', 'Line Manager'),
        ('hod', 'HOD'),
        ('custom', 'Custom'),
    ], string='Type', default='manager', required=True)
    user_id = fields.Many2one('res.users', string='Approver')    


class HrApprovalRequest(models.Model):
    _name = 'hr.approval.request'
    _description = 'HR Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    
    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company')
    category_id = fields.Many2one('category.approval', string='Category')
    model_id = fields.Char(string='Model')
    record_id = fields.Char(string='Record ID')
    user_id = fields.Many2one('res.users', string='Requested By')
    date = fields.Date(string='Date')
    description = fields.Char(string='Description') 
    approver_ids = fields.One2many('hr.approver.line', 'approver_id' ,string='Approver')
    state = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string='Status', default='new')
    
    
    def action_refuse(self):
        for line in self:
            approver_count = 0
            for approver in line.approver_ids:
                if approver.user_status=='pending':
                    approver.update({
                        'user_status': 'refused'
                    })
            model = self.env['ir.model'].sudo().search([('model','=',line.model_id)], limit=1) 
            record = self.env[model.model].search([('id','=',line.record_id)], limit=1)
            if model.model=='hr.expense.sheet':
                record.update({'state': 'cancel'})
                for linea in record.expense_line_ids:
                    linea.update({'state': 'cancel'})    
            else:
                record.action_refuse()
            return line.write({'state': 'refused'})

    def action_submit(self):
        approver_count = 0
        for approver in self.approver_ids:
            if approver.user_status=='new':
                approver.update({
                    'user_status': 'pending'
                })                 
                break;                
        self.write({'state': 'pending'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        for data in self:
            approver_count = 0
            for approver in self.approver_ids:
                if approver.user_status=='pending':
                    approver.update({
                        'user_status': 'approved'
                    })
                if approver.user_status=='new':
                    approver_count += 1
                    approver.update({
                    'user_status': 'pending'
                    })    
                    break;        
            if approver_count==0:
#                 raise UserError(str(approver_count)+' test '+)
                model = self.env['ir.model'].sudo().search([('model','=',self.model_id)], limit=1) 
                record = self.env[model.model].search([('id','=',data.record_id)], limit=1)
                if model.model=='hr.expense.sheet':
                    record.approve_expense_sheets()
                else:
                    record.action_approve()
                data.write({'state': 'approved'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('new', 'cancel'):
                raise ValidationError(
                    'You cannot delete a request which is not in draft or cancelled state')
        return super(HrApprovalRequest, self).unlink()
    
    
class HrApproverLine(models.Model):
    _name = 'hr.approver.line'
    _description = 'HR Approver Line'
    
    user_id = fields.Many2one('res.users', string='User', required=True)
    approver_id = fields.Many2one('hr.approval.request', string='Approval')    
    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string='Status', default='new')
    
    
    
