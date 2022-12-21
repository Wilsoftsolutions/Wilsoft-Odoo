# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime
import base64

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips, ResultRules
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

class HrPayslip(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one('hr.loan.line', string='Loan Lines')    

    

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
            
            
    def compute_sheet(self):
        for payslip in self: 
            for other_input in payslip.input_line_ids:
                if other_input.code in ('LOAN','ADVSAL'):
                    other_input.unlink()
            if payslip.contract_id:
                contracts = payslip.contract_id
                employee = payslip.employee_id
                date_from = payslip.date_from
                date_to = payslip.date_to
                data = []
                other_inputs = self.env['hr.payslip.input.type'].search([])
                contract_obj = self.env['hr.contract']
                emp_id = contract_obj.browse(contracts[0].id).employee_id
                lon_obj = self.env['hr.loan'].search([('employee_id', '=', emp_id.id), ('state', '=', 'approve')])
                for loan in lon_obj:
                    for loan_line in loan.loan_lines:
                        code_executing = loan_line.loan_id.loan_type_id.code
                        if date_from <= loan_line.date  and loan_line.date <= date_to:
                            for result in other_inputs:
                                if result.code == code_executing:  
                                    data.append((0,0,{
                                      'payslip_id': payslip.id,
                                      'sequence': 1,
                                      'code': result.code,
                                      'contract_id': payslip.contract_id.id,
                                      'input_type_id': result.id,
                                      'amount': loan_line.amount,
                                      'loan_line_id': loan_line.id   
                                    }))
                                    loan_line.update({
                                        'payslip_id': payslip.id,
                                        'paid': True,
                                    })
            payslip.input_line_ids = data
        res = super(HrPayslip, self).compute_sheet()
        return res
   


   