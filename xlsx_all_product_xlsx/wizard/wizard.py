from odoo import fields, models


class XlsxInventoryReports(models.TransientModel):
    _name = 'reports.xlsx.all'
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
        return self.env.ref('xlsx_all_product_xlsx.inventory_def_reports_xlsx_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.xlsx_all_product_xlsx.inventory_def_reports_xlsx_id"
    _inherit = "report.report_xlsx.abstract"
    _description = "Inventory XLSX Report"

    def generate_xlsx_report(self, workbook, data, docs):
        all_stock = self.env['stock.quant'].search([('location_id.usage', '=', 'internal',)])
        sheet = workbook.add_worksheet('Inventory xlsx Report')
        style0 = workbook.add_format({'align': 'left', 'border': True})
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 20, 'bg_color': '#f2eee4',
             'border': True})
        header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True, 'valign': 'vcenter', })
        row = 0
        col = 0
        all_internal_loc = self.env['stock.location'].search([('usage', '=', 'internal')])
        sheet.merge_range(row, col, row + 3, col + 12 + (len(all_internal_loc) * 2), 'All Inventory xlsx Report', title)
        row += 4
        # Header row
        sheet.set_column(0, 5, 18)
        sheet.merge_range(row, col, row + 1, col, 'Item Id', header_row_style)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'Store Name', header_row_style)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Item Category', header_row_style)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Item Code', header_row_style)
        sheet.merge_range(row, col + 4, row + 1, col + 5, 'Item Desc', header_row_style)
        sheet.merge_range(row, col + 6, row + 1, col + 7, 'Short Desc', header_row_style)
        sheet.merge_range(row, col + 8, row + 1, col + 9, 'Color Description', header_row_style)
        sheet.merge_range(row, col + 10, row + 1, col + 10, 'Color', header_row_style)
        sheet.merge_range(row, col + 11, row + 1, col + 11, 'Size', header_row_style)
        sheet.merge_range(row, col + 12, row + 1, col + 12, 'UOM', header_row_style)
        loc_col = 13
        for loc in all_internal_loc:
            warehouse = loc.warehouse_id.name if loc.warehouse_id else ''
            sheet.merge_range(row, loc_col, row + 1, loc_col + 1,
                              warehouse + '\n' + loc.name,
                              header_row_style)
            loc_col += 2
        sheet.merge_range(row, loc_col, row + 1, loc_col, 'Price', header_row_style)
        row += 2
        count = 1
        done_ids = []
        location_grand_total = []
        for stock in all_stock:
            if stock.product_id.id not in done_ids:
                product_attribute = stock.product_id.product_template_attribute_value_ids
                color_id = product_attribute.filtered(
                    lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                )
                size = product_attribute.filtered(
                    lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                )

                sheet.write(row, col, count, style0)
                sheet.write(row, col + 1, 'new', style0)
                if stock.product_id.qty_available > 0:
                    sheet.write(row, col + 1, stock.location_id.name if stock.location_id else '-',
                                style0)
                else:
                    sheet.write(row, col + 1, 'Shopify-001', style0)
                sheet.write(row, col + 2, stock.product_id.categ_id.complete_name.split('/')[0], style0)
                sheet.write(row, col + 3, stock.product_id.default_code if stock.product_id.default_code else '-',
                            style0)
                sheet.merge_range(row, col + 4, row, col + 5, stock.product_id.display_name, style0)
                sheet.merge_range(row, col + 6, row, col + 7, stock.product_id.name, style0)
                sheet.merge_range(row, col + 8, row, col + 9, color_id.name if color_id else '-', style0)
                sheet.write(row, col + 10, color_id.name if color_id else '-', style0)
                sheet.write(row, col + 11, size.name if size else '-', style0)
                sheet.write(row, col + 12, stock.product_id.uom_id.name if stock.product_id.uom_id else '-', style0)
                loc_location = 13
                i = 0
                for loc in all_internal_loc:
                    qty = stock.product_id.with_context(to_date=fields.Datetime.now(),
                                                        location=loc.id).qty_available
                    sheet.merge_range(row, loc_location, row, loc_location + 1, qty, style0)
                    loc_location += 2
                    if len(location_grand_total) < len(all_internal_loc):
                        location_grand_total.append(int(qty))
                    else:
                        location_grand_total[i] += int(qty)
                    i += 1
                sheet.write(row, loc_location, stock.product_id.list_price, style0)
                row += 1
                count += 1
                done_ids.append(stock.product_id.id)

        sheet.merge_range(row, col + 10, row + 1, col + 11, 'Grand Total', header_row_style)
        grand_col = 12
        for grand_total in location_grand_total:
            sheet.merge_range(row, grand_col, row + 1, grand_col + 1, grand_total, header_row_style)
            grand_col += 2
        sheet.merge_range(row, 0, row + 2, col + 12 + (len(all_internal_loc) * 2), 'Products With Zero Quantity',
                          header_row_style)
        remaining_products = self.env['product.product'].search([('id', 'not in', tuple(done_ids))])
        row += 3
        new_count = count
        for prod in remaining_products:
            product_attribute = prod.product_template_attribute_value_ids
            color_id = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
            )
            size = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
            )

            sheet.write(row, col, new_count, style0)
            sheet.write(row, col + 1, 'new', style0)
            if prod.qty_available > 0:
                sheet.write(row, col + 1, stock.location_id.name if stock.location_id else '-',
                            style0)
            else:
                sheet.write(row, col + 1, 'Shopify-001', style0)
            sheet.write(row, col + 2, prod.categ_id.complete_name.split('/')[0], style0)
            sheet.write(row, col + 3, prod.default_code if prod.default_code else '-',
                        style0)
            sheet.merge_range(row, col + 4, row, col + 5, stock.product_id.display_name, style0)
            sheet.merge_range(row, col + 6, row, col + 7, stock.product_id.name, style0)
            sheet.merge_range(row, col + 8, row, col + 9, color_id.name if color_id else '-', style0)
            sheet.write(row, col + 10, color_id.name if color_id else '-', style0)
            sheet.write(row, col + 11, size.name if size else '-', style0)
            sheet.write(row, col + 12, prod.uom_id.name if prod.uom_id else '-', style0)
            loc_location = 13
            for loc in all_internal_loc:
                qty = 0
                sheet.merge_range(row, loc_location, row, loc_location + 1, qty, style0)
                loc_location += 2
            sheet.write(row, loc_location, prod.list_price, style0)
            row += 1
            new_count += 1

