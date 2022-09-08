from odoo import fields, models


class XlsxSaleReports(models.TransientModel):
    _name = 'sale.return.wizard'
    _description = 'Sale Return Report'

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
            'model': 'reports.xlsx',
            'data': data
        }
        return self.env.ref('sale_return_report.sale_return_report_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.sale_return_report.sale_return_report"
    _inherit = "report.report_xlsx.abstract"
    _description = "Sale Return Report"

    def get_tax(self, line=None):
        line_tax = 0
        for tax in line.tax_ids:
            line_tax += line.price_subtotal * (tax.amount / 100)
        return line_tax

    def generate_xlsx_report(self, workbook, data, docs):
        domain = [('move_type', '=', 'out_refund')]
        if data['data']['date_from']:
            domain.append(('create_date', '>=', data['data']['date_from']))
        if data['data']['date_to']:
            domain.append(('create_date', '<=', data['data']['date_to']))
        credit_notes = self.env['account.move'].sudo().search(domain)
        sheet = workbook.add_worksheet('Sale Return Report')
        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#fffbed', 'border': True})
        style0 = workbook.add_format({'align': 'left', 'border': True})
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 20, 'bg_color': '#D2EC44',
             'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True, 'valign': 'vcenter', })
        num_fmt = workbook.add_format({'num_format': '#,####', 'align': 'left', 'border': True})
        row = 0
        col = 0
        sheet.merge_range(row, col, row + 3, col + 23, 'Sale Return Report', title)

        row += 4
        # Header row
        sheet.set_column(0, 5, 18)
        sheet.merge_range(row, col, row + 1, col, 'Order #', header_row_style)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'Customer Name', header_row_style)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Item Code', header_row_style)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Article', header_row_style)
        sheet.merge_range(row, col + 4, row + 1, col + 4, 'Invoice Status', header_row_style)
        sheet.merge_range(row, col + 5, row + 1, col + 5, 'Invoice Date', header_row_style)
        sheet.merge_range(row, col + 6, row + 1, col + 7, 'Item Category', header_row_style)
        sheet.merge_range(row, col + 8, row + 1, col + 8, 'Qty', header_row_style)
        sheet.merge_range(row, col + 9, row + 1, col + 10, 'Sale Team', header_row_style)
        sheet.merge_range(row, col + 11, row + 1, col + 12, 'Shipping City', header_row_style)
        sheet.merge_range(row, col + 13, row + 1, col + 14, 'Billing City', header_row_style)
        sheet.merge_range(row, col + 15, row + 1, col + 15, 'Color', header_row_style)
        sheet.merge_range(row, col + 16, row + 1, col + 16, 'Size', header_row_style)
        sheet.merge_range(row, col + 17, row + 1, col + 17, 'UOM', header_row_style)
        sheet.merge_range(row, col + 18, row + 1, col + 18, 'Category', header_row_style)
        sheet.merge_range(row, col + 19, row + 1, col + 19, 'Invoice No.', header_row_style)
        sheet.merge_range(row, col + 20, row + 1, col + 21, 'Entered Amount', header_row_style)
        sheet.merge_range(row, col + 22, row + 1, col + 23, 'Invoice Balance', header_row_style)

        row += 2
        count = 1
        grand_total = 0

        # putting data started from here
        for ret in credit_notes:
            for line in ret.invoice_line_ids:
                line_tax = self.get_tax(line) if line.tax_ids else 0
                product_attribute = line.product_id.product_template_attribute_value_ids
                color_id = product_attribute.filtered(
                    lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                )
                size = product_attribute.filtered(
                    lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                )
                addr = ret.partner_id.city
                sheet.write(row, col, ret.invoice_origin if ret.invoice_origin else '-', style0)
                sheet.write(row, col + 1, ret.partner_id.name if ret.partner_id else None, style0)
                sheet.write(row, col + 2, line.product_id.default_code, style0)
                sheet.write(row, col + 3, line.product_id.name if line.product_id.name else '-', style0)
                sheet.write(row, col + 4, ret.state if ret.state else None, style0)
                sheet.write(row, col + 5, str(ret.invoice_date) if ret.invoice_date else '-', style0)
                sheet.merge_range(row, col + 6, row, col + 7, line.product_id.categ_id.complete_name.split('/')[
                    0] if line.product_id.categ_id else '-', style0)
                sheet.write(row, col + 8, line.quantity, style0)
                sheet.merge_range(row, col + 9, row, col + 10, ret.team_id.name if ret.team_id else None, num_fmt)
                sheet.merge_range(row, col + 11, row, col + 12, addr, style0)
                sheet.merge_range(row, col + 13, row, col + 14, addr, style0)
                sheet.write(row, col + 15, color_id.name if color_id else '-', style0)
                sheet.write(row, col + 16, size.name if size else '-', style0)
                sheet.write(row, col + 17, line.product_uom_id.name, style0)
                sheet.write(row, col + 18, line.product_id.categ_id.complete_name, style0)
                sheet.write(row, col + 19, ret.name, style0)
                sheet.merge_range(row, col + 20, row, col + 21, line.price_subtotal, num_fmt)
                sheet.merge_range(row, col + 22, row, col + 23, line_tax + line.price_subtotal, num_fmt)
                grand_total += line_tax + line.price_subtotal

                row += 1
                count += 1

        sheet.merge_range(row, col + 20, row + 1, col + 21, 'Grand Total', header_row_style)
        sheet.merge_range(row, col + 22, row + 1, col + 23, grand_total, header_row_style)
