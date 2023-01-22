# # -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MaterialReportWizard(models.Model):
    _name = 'material.report.wizard'
    _description = 'Material Report Wizard'
    
    
    date_from = fields.Date(string='Date From', required=True,  default=fields.date.today().replace(day=1) )
    date_to = fields.Date(string='Date To', required=True,  default=fields.date.today() )
    partner_id = fields.Many2one('res.partner', string='Customer')
    status = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('waiting_for_approval', 'Waiting For Approval'),
            ('waiting_ware_house_approval', 'Waiting W/H Approval'),
            ('approved', 'Approved'),
            ('cancelled', 'Rejected'),
        ], string='Status'
        )
    
   
    def check_report(self):
        data = {}
        data['form'] = self.read(['date_from','date_to','status','partner_id'])[0]
        return self._print_report(data)

    
    def _print_report(self, data):
        data['form'].update(self.read(['date_from','date_to','status','partner_id'])[0])
        return self.env.ref('ws_material_request_report.open_material_report').report_action(self, data=data, config=False)