# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta



class WHTReportWizard(models.Model):
    _name = 'wht.report.wizard'
    _description = 'WHT Report Wizard'
     

    company_id = fields.Many2one('res.company',  string='Company',  required=True,  default=lambda self: self.env.company)
    date_from =  fields.Date(string='Date',  required=True )
    date_to =  fields.Date(string='Date',  required=True )
    
    
    def check_report(self):
        data = {}
        data['form'] = self.read(['company_id','date_from','date_to'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['company_id','date_from','date_to'])[0])
        return self.env.ref('de_payment_taxes.open_pay_tax_wht_action').report_action(self, data=data, config=False)





