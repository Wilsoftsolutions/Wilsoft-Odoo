# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"



    def _compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid==True:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

    name = fields.Char(string="Loan Name", default="/", readonly=True, help="Name of the loan")
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee",)
    approval_request_id = fields.Many2one('hr.approval.request', string="Approval Request")
    
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department", help="Employee")
    installment = fields.Integer(string="Duration(Months)", default=1, help="Number of installments")
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today(), help="Date of "
                                                                                                             "the "
                                                                                                             "paymemt")
    loan_type_id = fields.Many2one('hr.loan.type', 'Loan Type', required=True, help="Loan",)

    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position",
                                   help="Job position")
    loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount")
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount',
                                help="Total loan amount")
    balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_loan_amount', help="Balance amount")
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_loan_amount',
                                     help="Total paid amount")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )
    
    
    @api.constrains('loan_amount')
    def _check_loan_amount(self):
        for line in self:
            loan_exist = self.env['hr.loan'].search([('employee_id','=',line.employee_id.id),('date','>', line.date-timedelta(30) ),('state','!=','draft')], limit=1)
            if loan_exist and line.loan_type_id.per_month==True:
                raise UserError('Already Loan Request Exist in System! '+ str(loan_exist.name)+' Not Allow to request Advance twice in a single month. Please Select Date greater than '+str(loan_exist.date+timedelta(30)))
            contract = self.env['hr.contract'].search([('employee_id','=',line.employee_id.id),('state','=','open')], limit=1)
            if contract:
                amount_limit = ((contract.wage)/100) * line.loan_type_id.percentage
                if line.loan_amount > amount_limit and line.loan_type_id.percentage > 0:
                    raise UserError('Not Allow to Submit Advance Amount Greater than '+str(amount_limit) )
    
    
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
        
        res = super(HrLoan, self).create(values)
        res.action_submit()
        return res
    
    
    
    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': round(amount,0),
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            loan._compute_loan_amount()
        return True

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        for line in self:
            if line.installment > line.loan_type_id.installment or line.installment < 0:
                raise UserError('Not Allow to Select Installment Greater than '+str(line.loan_type_id.installment)+' or less than zero!')
            if line.installment==0:
                line.update({
                    'installment': line.loan_type_id.installment,
                })
            servicedata = self.env['category.approval'].sudo().search([('name','=',line.name),('company_id','=',line.employee_id.company_id.id)], limit=1)
            if not servicedata:
                categ_vals = {
                    'name': line.loan_type_id.name,
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
                    'name': str(line.loan_type_id.name)+' For Amount '+str(line.loan_amount)+' Date '+str(line.date),
                    'description': str(line.loan_amount)+' Date '+str(line.date),
                    'user_id': line.employee_id.user_id.id,
                    'model_id': 'hr.loan',
                    'record_id': line.id,
                    'category_id': servicedata.id,
                    'date': line.date,
                    'company_id': line.employee_id.company_id.id,
                }  
                approval = self.env['hr.approval.request'].sudo().create(approval_vals)

                if line.employee_id.is_hr_approval==True and line.employee_id.company_id.hr_id.user_id:
                    approver_vals = {
                        'user_id': line.employee_id.company_id.hr_id.user_id.id  ,
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
            data.compute_installment()
            vals = {
            'partner_id': data.employee_id.address_home_id.id,            
            'date': data.date,
            'journal_id': self.env['account.journal'].sudo().search([('company_id','=',data.employee_id.company_id.id),('name','=','Cash in hand with Cashier')], limit=1).id,
            'amount': data.loan_amount,
            'ref': data.name,
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
    
    
    
    
    
class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
    amount = fields.Float(string="Amount", required=True, help="Amount")
    paid = fields.Boolean(string="Paid", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip") 
    

    
    
class HrLoanType(models.Model):
    _name = 'hr.loan.type'
    _description = 'Loan Type'    
    
    name = fields.Char(string="Name", required=True)
    installment = fields.Integer(string='Installment')
    code = fields.Char(string='Code')
    per_month = fields.Boolean(string='Limit Per Month')
    percentage = fields.Float(string='Percentage Of Salary')
    
