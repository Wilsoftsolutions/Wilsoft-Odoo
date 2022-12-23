# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta


class HREmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    leave_ded = fields.Boolean(string='Not Leave Deduction')
    stop_salary = fields.Boolean(string='Stop Salary')
      
    is_advance_expense = fields.Boolean(string='Advance Expense')
    employee_family_ids = fields.One2many('hr.employee.family', 'employee_id', string='Employee Family')
    

class HREmployee(models.Model):
    _inherit = 'hr.employee'
    
    leave_ded = fields.Boolean(string='Not Leave Deduction')
    stop_salary = fields.Boolean(string='Stop Salary')
    policy_id = fields.Many2one('hr.policy.configuration', string='Policy')
    
    
    def action_send_reminder_email_notification(self):
        companies = self.env['res.company'].search([])
        for company in companies:
            employees = self.env['hr.employee'].search([('company_id' ,'=', company.id)])
            for emp in employees:
                # Retirement Age Portion
                total_service_days = 365 * emp.company_id.retirement_age
                check_start_date = fields.date.today()+ timedelta(60)
                check_end_date = emp.birthday if emp.birthday else fields.date.today()
                calculated_days = (check_start_date - check_end_date).days
                if calculated_days > total_service_days:
                    emp.action_send_mail_reminder_retirement_age() 
                check_start_date = fields.date.today() + timedelta(30)  
                calculated_days = (check_start_date - check_end_date).days
                if calculated_days > total_service_days:
                    emp.action_send_mail_reminder_retirement_age()
                check_start_date = fields.date.today() + timedelta(4)  
                calculated_days = (check_start_date - check_end_date).days
                if calculated_days > total_service_days:
                    emp.action_send_mail_reminder_retirement_age()    
                # Birth Day Portion
                if str( (fields.date.today() + timedelta(6)).strftime('%d-%m')) == str(emp.birthday.strftime('%d-%m') if emp.birthday else fields.date.today().strftime('%d-%m') ):
                    emp.action_send_mail_reminder_hr()
                    emp.action_send_mail_reminder()
                if str( (fields.date.today() + timedelta(3)).strftime('%d-%m')) == str(emp.birthday.strftime('%d-%m') if emp.birthday else fields.date.today().strftime('%d-%m') ):
                    emp.action_send_mail_reminder_hr()
                    emp.action_send_mail_reminder()    
                # Work Anniversary Portion
                if str( (fields.date.today() + timedelta(6)).strftime('%d-%m')) == str(emp.x_studio_doj.strftime('%d-%m') if emp.x_studio_doj else  fields.date.today().strftime('%d-%m') ):
                    emp.action_send_mail_reminder_work_day_hr()
                    emp.action_send_mail_reminder_work_day()
                if str( (fields.date.today() + timedelta(3)).strftime('%d-%m')) == str(emp.x_studio_doj.strftime('%d-%m') if emp.x_studio_doj else  fields.date.today().strftime('%d-%m') ):
                    emp.action_send_mail_reminder_work_day_hr()
                    emp.action_send_mail_reminder_work_day()    
                # Probation End Notification
                if str( (fields.date.today() + timedelta(6))) == str(emp.x_studio_probation_due_date):
                    emp.action_send_mail_reminder_probation_notification()
                if str( (fields.date.today() + timedelta(3))) == str(emp.x_studio_probation_due_date):
                    emp.action_send_mail_reminder_probation_notification()    

                    

                    
            
    
    
    
    
    def action_send_mail_reminder(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_birth_day')
        ctx = {
            'employee_to_name': self.name,
            'recipient_users': self.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()
        
        
    def action_send_mail_reminder_hr(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_birth_day_hr')
        ctx = {
            'employee_to_name': self.company_id.hr_id.name,
            'recipient_users': self.company_id.hr_id.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.company_id.hr_id.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()    
        
        
    
    def action_send_mail_reminder_work_day_hr(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_work_day_hr')
        ctx = {
            'employee_to_name': self.company_id.hr_id.name,
            'recipient_users': self.company_id.hr_id.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.company_id.hr_id.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()    

        
    def action_send_mail_reminder_work_day(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_work_day')
        ctx = {
            'employee_to_name': self.name,
            'recipient_users': self.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()    
      
    
    
    def action_send_mail_reminder_retirement_age(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_retirement_age')
        ctx = {
            'employee_to_name': self.company_id.hr_id.name,
            'recipient_users': self.company_id.hr_id.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.company_id.hr_id.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()    
        
        
        
    def action_send_mail_reminder_probation_notification(self):
        mail_template = self.env.ref('de_hr_payroll_policy.mail_template_employee_probation_notification')
        ctx = {
            'employee_to_name': self.company_id.hr_id.name,
            'recipient_users': self.company_id.hr_id.user_id,
            'url': '/mail/view?model=%s&res_id=%s' % ('hr.employee', self.id),
        }
        RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
        subject = RenderMixin._render_template(mail_template.subject, 'hr.employee', self.ids, post_process=True)[self.id]
        body = RenderMixin._render_template(mail_template.body_html, 'hr.employee', self.ids, post_process=True)[self.id]
        
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'auto_delete': True,
            'email_to': self.company_id.hr_id.work_email
        }
        activity= self.env['mail.mail'].sudo().create(mail_values)
        activity.send()        
    
    employee_family_ids = fields.One2many('hr.employee.family', 'employee_id', string='Employee Family')


class HrEmployeeFamily(models.Model):

    _name = 'hr.employee.family'
    _description = "Employee Family"



    name = fields.Char(string="Name",required=True)
    mobile = fields.Char(string="Mobile")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    relation_ship = fields.Selection([('father','Father'),
                                      ('mother','Mother'),
                                      ('brother','Brother'),
                                      ('sister','Sister'),
                                      ('husband','Husband'),
                                      ('wife','Wife'),
                                      ('child','Child')], string='Relationship',required=True, default='father')

    employee_id = fields.Many2one('hr.employee', string='Employee')
    date_of_birth = fields.Date(string='Date Of Birth')
    
   


