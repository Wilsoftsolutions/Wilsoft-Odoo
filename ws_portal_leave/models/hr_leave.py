# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    fiscal_year = fields.Char(related='holiday_status_id.fiscal_year')
    leave_category = fields.Selection([
        ('day', 'Day'),
        ('half_day', 'Half Day'),
        ('hours', 'Short leave'),
        ], string='Leave Category', tracking=True)
    leave_period_half = fields.Selection([
        ('first_half', 'First Half'),
        ('second_half', 'Second Half'),
        ], string='Half', tracking=True)
    approval_request_id = fields.Many2one('hr.approval.request', string='Request')
    attachment_id = fields.Many2many('ir.attachment', relation="files_rel_leave",
                                            column1="doc_id",
                                            column2="attachment_id",
                                            string="Attachment")
    short_start_time = fields.Char(string='Time From')
    
    def action_confirm_data(self):
        if self.holiday_status_id.category_id:
            approval_vals = {
                'name': 'Duration '+str(self.number_of_days)+' Days',
                'description': 'Reason '+str(self.name),
                'user_id': self.employee_id.user_id.id,
                'model_id': 'hr.leave',
                'record_id': self.id,
                'category_id': self.holiday_status_id.category_id.id,
                'date': fields.date.today(),
                'company_id': self.employee_id.company_id.id,
            }  
            approval = self.env['hr.approval.request'].sudo().create(approval_vals)
            if self.employee_id.is_hr_approval==True and self.employee_id.company_id.hr_id:
                approver_vals = {
                    'user_id': self.employee_id.company_id.hr_id.id  ,
                    'approver_id': approval.id,
                    'user_status': 'new',
                }
                approver_line = self.env['hr.approver.line'].sudo().create(approver_vals) 
            else: 
                for approver in self.holiday_status_id.category_id.approver_ids:
                    user = approver.user_id.id
                    if approver.user_type=='manager':
                        user = self.employee_id.parent_id.user_id.id 
                    if approver.user_type=='hod':
                        user = self.employee_id.department_id.manager_id.user_id.id 
                    if not user:
                        raise UserError('You are not Allow to submit Request.User Configuration missing on Approval category or Employee Profile. Please contact to the HR Department.')
                    approver_vals = {
                        'user_id': user,
                        'approver_id': approval.id,
                        'user_status': 'new',
                    }
                    approver_line = self.env['hr.approver.line'].sudo().create(approver_vals)
            approval.action_submit()
            self.update({
                'approval_request_id': approval.id,
            })
       