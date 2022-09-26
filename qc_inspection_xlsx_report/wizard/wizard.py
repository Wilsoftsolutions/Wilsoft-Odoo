from odoo import fields, models
from datetime import datetime


class XlsxQCInspectionReports(models.TransientModel):
    _name = 'reports.qc.xlsx'
    _description = 'Description'

    date_from = fields.Date('Date from', default=fields.Datetime.now())
    date_to = fields.Date('Date to', default=fields.Datetime.now())

    def get_print_data(self):
        data = {
            "date_from": self.date_from,
            "date_to": self.date_to,
        }
        active_ids = self.env.context.get('active_ids', [])

        datas = {
            'ids': active_ids,
            'model': 'reports.qc.xlsx',
            'data': data
        }
        return self.env.ref('qc_inspection_xlsx_report.qc_def_reports_xlsx_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.qc_inspection_xlsx_report.qc_reports_xlsx_id"
    _inherit = "report.report_xlsx.abstract"
    _description = "Qc XLSX Report"

    def generate_xlsx_report(self, workbook, data, docs):
        domain = []
        if data['data']['date_from']:
            domain.append(('x_studio_date', '>=', data['data']['date_from']))
        if data['data']['date_to']:
            domain.append(('x_studio_date', '<=', data['data']['date_to']))
        qc_all = self.env['qc.inspection'].sudo().search(domain)
        sheet = workbook.add_worksheet('QC xlsx Report')
        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#fffbed', 'border': True})
        style0 = workbook.add_format({'align': 'center', 'border': True})
        date_style = workbook.add_format({'text_wrap': True, 'num_format': 'dd-mm-yyyy','align': 'center', 'border': True})
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 20, 'bg_color': '#f2eee4',
             'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True, 'valign': 'vcenter', })
        num_fmt = workbook.add_format({'num_format': '#,####', 'align': 'center', 'border': True})
        row = 0
        col = 0
        sheet.merge_range(row, col, row + 3, col + 12, 'QC xlsx Report', title)

        row += 4
        # Header row
        sheet.set_column(0, 5, 18)
        sheet.merge_range(row, col, row + 1, col, 'Date', header_row_style)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'QC Inspector', header_row_style)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Suppliers', header_row_style)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Article', header_row_style)
        sheet.merge_range(row, col + 4, row + 1, col + 4, 'Plan QTY', header_row_style)
        sheet.merge_range(row, col + 5, row + 1, col + 5, 'Check QTY', header_row_style)
        sheet.merge_range(row, col + 6, row + 1, col + 7, 'Re-Work', header_row_style)
        sheet.merge_range(row, col + 8, row + 1, col + 8, 'B.Pairs', header_row_style)
        sheet.merge_range(row, col + 9, row + 1, col + 10, 'Balanced', header_row_style)
        sheet.merge_range(row, col + 11, row + 1, col + 12, 'Closing Comments', header_row_style)

        row += 2
        count = 1
        grand_total = 0
        for inv in qc_all:
            check_total = (inv.check36 + inv.check37 + inv.check38 +
                           inv.check39 + inv.check40 + inv.check41 +
                           inv.check42 + inv.check43 + inv.check44+
                           inv.check45 + inv.check46
                           )
            rework_total = (inv.rework36 + inv.rework37 + inv.rework38 +
                           inv.rework39 + inv.rework40 + inv.rework41 +
                           inv.rework42 + inv.rework43 + inv.rework44 +
                           inv.rework45 + inv.rework46
                           )
            bpair_total = (inv.bpair36 + inv.bpair37 + inv.bpair38 +
                            inv.bpair39 + inv.bpair40 + inv.bpair41 +
                            inv.bpair42 + inv.bpair43 + inv.bpair44 +
                            inv.bpair45 + inv.bpair46
                            )
            bal_total = (inv.bal_36 + inv.bal_37 + inv.bal_38 +
                           inv.bal_39 + inv.bal_40 + inv.bal_41 +
                           inv.bal_42 + inv.bal_43 + inv.bal_44 +
                           inv.bal_45 + inv.bal_46
                           )

            sheet.write(row, col, inv.x_studio_date, date_style)
            sheet.write(row, col + 1, inv.x_studio_qc_inspector.name, style0)
            sheet.write(row, col + 2, inv.vendor_id.name, style0)
            sheet.write(row, col + 3, inv.po_item_id.name if inv.po_item_id.name else '-', style0)
            sheet.write(row, col + 4, inv.plan, style0)
            sheet.write(row, col + 5, check_total, style0)
            sheet.merge_range(row, col + 6, row, col + 7, rework_total, style0)
            sheet.write(row, col + 8, bpair_total, style0)
            sheet.merge_range(row, col + 9, row, col + 10, bal_total, num_fmt)
            sheet.merge_range(row, col + 11, row, col + 12, inv.comment, style0)
            row += 1


