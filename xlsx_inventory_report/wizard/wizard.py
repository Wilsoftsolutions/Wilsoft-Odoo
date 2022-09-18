from odoo import fields, models


class XlsxInventoryReports(models.TransientModel):
    _name = 'reports.xlsx'
    _description = 'Description'

    category_id = fields.Many2one('product.category', string='Product Category')
    location_id = fields.Many2one('stock.location', string='Location')

    def get_print_data(self):
        data = {
            "category_id": self.category_id.id,
            "location_id": self.location_id.id
        }
        active_ids = self.env.context.get('active_ids', [])

        datas = {
            'ids': active_ids,
            'model': 'reports.xlsx',
            'data': data
        }
        return self.env.ref('xlsx_inventory_report.inventory_def_reports_xlsx_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.xlsx_inventory_report.inventory_def_reports_xlsx_id"
    _inherit = "report.report_xlsx.abstract"
    _description = "Inventory XLSX Report"

    def generate_xlsx_report(self, workbook, data, docs):
        if data['data']['category_id'] and data['data']['location_id']:
            stock = self.env['stock.quant'].search(
                [('product_id.categ_id.id', '=', data['data']['category_id']),
                 ('location_id.id', '=', data['data']['location_id'])])

        elif data['data']['category_id'] and not data['data']['location_id']:
            stock = self.env['stock.quant'].search(
                [('product_id.categ_id.id', '=', data['data']['category_id'])])

        elif data['data']['location_id'] and not data['data']['category_id']:
            stock = self.env['stock.quant'].search(
                [('location_id.id', '=', data['data']['location_id'])])
        else:
            stock = self.env['stock.quant'].search([])

        sheet = workbook.add_worksheet('Inventory xlsx Report')
        style0 = workbook.add_format({'align': 'left', 'border': True})
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 20, 'bg_color': '#f2eee4',
             'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True, 'valign': 'vcenter', })
        row = 0
        col = 0
        sheet.merge_range(row, col, row + 3, col + 16, 'Inventory xlsx Report', title)

        row += 4
        # Header row
        sheet.set_column(0, 5, 18)
        sheet.merge_range(row, col, row + 1, col, 'Item Id', header_row_style)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'Brand', header_row_style)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Item Category', header_row_style)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Item Code', header_row_style)
        sheet.merge_range(row, col + 4, row + 1, col + 5, 'Item Desc', header_row_style)
        sheet.merge_range(row, col + 6, row + 1, col + 7, 'Short Desc', header_row_style)
        sheet.merge_range(row, col + 8, row + 1, col + 9, 'Color', header_row_style)
        sheet.merge_range(row, col + 10, row + 1, col + 10, 'Size', header_row_style)
        sheet.merge_range(row, col + 11, row + 1, col + 11, 'Qty', header_row_style)
        sheet.merge_range(row, col + 12, row + 1, col + 13, 'Locator', header_row_style)
        sheet.merge_range(row, col + 14, row + 1, col + 14, 'Uom', header_row_style)
        sheet.merge_range(row, col + 15, row + 1, col + 15, 'Price', header_row_style)
        sheet.merge_range(row, col + 16, row + 1, col + 16, 'Total', header_row_style)
        row += 2
        count = 1
        grand_total = 0
        for stock in stock:
            product_attribute = stock.product_id.product_template_attribute_value_ids
            color_id = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
            )
            size = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
            )

            sheet.write(row, col, count, style0)
            sheet.write(row, col + 1, stock.product_id.categ_id.complete_name.split('/')[0], style0)
            sheet.write(row, col + 2, stock.product_id.categ_id.name, style0)
            sheet.write(row, col + 3, stock.product_id.default_code if stock.product_id.default_code else '-', style0)
            sheet.merge_range(row, col + 4, row, col + 5, stock.product_id.display_name, style0)
            sheet.merge_range(row, col + 6, row, col + 7, stock.product_id.name, style0)
            sheet.merge_range(row, col + 8, row, col + 9, color_id.name if color_id else '-', style0)
            sheet.write(row, col + 10, size.name if size else '-', style0)
            sheet.write(row, col + 11, stock.quantity, style0)
            sheet.merge_range(row, col + 12, row, col + 13,
                              stock.location_id.warehouse_id.name if stock.location_id.warehouse_id else '-', style0)
            sheet.write(row, col + 14, stock.product_id.uom_id.name, style0)
            sheet.write(row, col + 15, stock.product_id.lst_price, style0)
            sheet.write(row, col + 16, stock.product_id.lst_price * stock.quantity, style0)
            grand_total += stock.product_id.lst_price * stock.quantity
            row += 1
            count += 1

        # grand total
        sheet.merge_range(row, col + 14, row + 1, col + 15, 'Grand Total', header_row_style)
        sheet.merge_range(row, col + 16, row + 1, col + 16, grand_total, header_row_style)

