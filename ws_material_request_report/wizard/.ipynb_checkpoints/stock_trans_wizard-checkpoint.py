# # -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TransferReportWizard(models.Model):
    _name = 'transfer.report.wizard'
    _description = 'Transfer Report Wizard'
    
    
    date_from = fields.Datetime(string='Date From', required=True,  default=fields.date.today().replace(day=1) )
    date_to = fields.Datetime(string='Date To', required=True,  default=fields.date.today() )
    categ_id = fields.Many2one('product.category', string='Category')
    location_ids = fields.Many2many('stock.location', string='Locations')
    
   
    def check_report(self):
        data = {}
        data['form'] = self.read(['date_from','date_to','categ_id','location_ids'])[0]
        return self._print_report(data)

    
    def _print_report(self, data):
        data['form'].update(self.read(['date_from','date_to','categ_id','location_ids'])[0])
        return self.env.ref('ws_material_request_report.open_transfer_report').report_action(self, data=data, config=False)