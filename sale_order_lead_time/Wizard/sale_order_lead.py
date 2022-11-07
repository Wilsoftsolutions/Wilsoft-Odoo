import datetime

from odoo import fields, models


class XlsxInventoryReports(models.TransientModel):
    _name = 'report.sale.order.lead.xlsx'
    _description = 'Description'

    date_from = fields.Date('Date from', default=fields.Datetime.now())
    date_to = fields.Date('Date to', default=fields.Datetime.now())

    def get_print_data(self):
        data = {
            "date_from": self.date_from,
            "date_to": self.date_to
        }
        active_ids = self.env.context.get('active_ids', [])

        datas = {
            'ids': active_ids,
            'model': 'report.sale.order.lead.xlsx',
            'data': data
        }
        return self.env.ref('sale_order_lead_time.sale_order_lead_time_report_xlsx_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.sale_order_lead_time.sale_order_lead_time_id"
    _inherit = "report.report_xlsx.abstract"
    _description = "Sale Order Lead Time"

    def generate_xlsx_report(self, workbook, data, docs):
        domain = []
        if data['data']['date_from']:
            domain.append(('date_order', '>=', data['data']['date_from']))
        if data['data']['date_to']:
            domain.append(('date_order', '<=', data['data']['date_to']))
        domain.append(('state', 'in', ['sale', 'done']))
        sales = self.env['sale.order'].sudo().search(domain)

        sheet = workbook.add_worksheet('Sale Order Lead Time')
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 15, 'bg_color': '#d4780f',
             'color': 'white',
             'border': True})
        title1 = workbook.add_format(
            {'bold': True, 'align': 'center', 'bg_color': '#130d69',
             'color': 'white',
             'border': True})
        title2 = workbook.add_format(
            {'align': 'center'})

        # Width to Columns
        sheet.set_column(0, 0, 20)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 20)
        sheet.set_column(3, 3, 20)
        sheet.set_column(4, 4, 15)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 8, 15)
        sheet.set_column(9, 9, 20)
        sheet.set_row(0, 20)

        # Merge Columns
        sheet.merge_range(0, 0, 0, 9, 'Order Processing/ Order Cycle', title)
        sheet.write(1, 0, 'Reference', title1)
        sheet.write(1, 1, 'Source Document', title1)
        sheet.write(1, 2, ' Location', title1)
        sheet.write(1, 3, 'Order Date', title1)
        sheet.write(1, 4, 'Approval Date', title1)
        sheet.write(1, 5, 'Approve Days', title1)
        sheet.write(1, 6, ' Delivery Date', title1)
        sheet.write(1, 7, 'Deliver Days', title1)
        sheet.write(1, 8, 'Invoice Date', title1)
        sheet.write(1, 9, 'Invoice Days', title1)

        rec_list = []
        sales = self.env['sale.order'].sudo().search(domain)
        today_date = datetime.date.today()
        delivery_approve_days = 0
        invoice_approve_days = 0
        order_approve_days = 0
        for rec in sales:
            invoice = self.env['account.move'].search([('invoice_origin', '=', rec.name)], limit=1)
            delivery = self.env['stock.picking'].search([('origin', '=', rec.name)], limit=1)
            if rec.approve_date:
                order_approve_days = rec.create_date.date() - rec.approve_date
            if delivery:
                if delivery.date_done and rec.date_order:
                    delivery_approve_days = rec.create_date.date() - delivery.date_done.date()
            else:
                delivery_approve_days = 0

            if invoice:
                if invoice.invoice_date and rec.date_order:
                    invoice_approve_days = rec.create_date.date() - invoice.invoice_date
            else:
                invoice_approve_days = 0

            rec_list.append({
                'ref': rec.name,
                'source_doc': delivery.name,
                'location': delivery.location_id.display_name,
                'order_date': str(rec.create_date.date()),
                'approval_date': str(rec.approve_date) if rec.approve_date else '-',
                'approval_days': order_approve_days if order_approve_days else 0,
                'delivery_date': str(delivery.date_done.date()) if delivery.date_done else '-',
                'invoice_date': str(invoice.invoice_date) if invoice.invoice_date else '-',
                'delivery_approve_days': delivery_approve_days,
                'invoice_approve_days': invoice_approve_days,
            })
        row = 1
        for line in rec_list:
            row += 1
            sheet.write(row, 0, line['ref'], title2)
            sheet.write(row, 1, line['source_doc'], title2)
            sheet.write(row, 2, line['location'], title2)
            sheet.write(row, 3, str(line['order_date']) if str(line['order_date']) else '-', title2)
            sheet.write(row, 4, str(line['approval_date']) if str(line['approval_date']) else '-', title2)
            sheet.write(row, 5, abs(line['approval_days']), title2)
            sheet.write(row, 6, str(line['delivery_date']) if str(line['delivery_date']) else '-', title2)
            sheet.write(row, 7, abs(line['delivery_approve_days']), title2)
            sheet.write(row, 8, str(line['invoice_date']) if str(line['invoice_date']) else '-', title2)
            sheet.write(row, 9, abs(line['invoice_approve_days']), title2)
