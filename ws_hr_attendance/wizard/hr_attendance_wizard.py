# -*- coding: utf-8 -*-

from odoo import api, fields, models, _



class HrAttendanceReportWizard(models.TransientModel):
    _name = "attendance.report.wizard"
    _description = "Attendance Report wizard"

    employee_ids = fields.Many2many('hr.employee', string='Employee')
    start_date = fields.Date(string='From Date', required='1', help='select start date')
    end_date = fields.Date(string='To Date', required='1', help='select end date')
    

    def check_report(self):
        data = {}
        data['form'] = self.read(['start_date', 'end_date','employee_ids'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['start_date', 'end_date','employee_ids'])[0])
        return self.env.ref('ws_hr_attendance.open_hr_report_wizard_action').report_action(self, data=data, config=False)