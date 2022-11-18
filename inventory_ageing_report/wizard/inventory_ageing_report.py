from datetime import datetime

from odoo import fields, models


class XlsxInventoryAgiengReports(models.TransientModel):
    _name = 'reports.inventory.ageing.xlsx'
    _description = 'Description'

    date_from = fields.Date('Date from', required=True)
    location_id = fields.Many2one('stock.location', string='Location')

    def get_print_data(self):
        data = {
            "date_from": self.date_from,
            "location_id": self.location_id.id,
        }
        active_ids = self.env.context.get('active_ids', [])

        datas = {
            'ids': active_ids,
            'model': 'reports.inventory.ageing.xlsx',
            'data': data
        }
        return self.env.ref('inventory_ageing_report.inventory_ageing_report_xlsx_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.inventory_ageing_report.inventory_ageing_id"
    _inherit = "report.report_xlsx.abstract"
    _description = "Inventory XLSX Report"

    def generate_xlsx_report(self, workbook, data, docs):
        sheet = workbook.add_worksheet('Inventory Ageing Report')
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 15, 'bg_color': '#191948',
             'color': 'white',
             'border': True})
        title1 = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#a1a1de',
             'color': 'white',
             'border': True})
        title2 = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'border': True})

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
        sheet.set_column(9, 9, 21)
        sheet.set_row(0, 21)
        sheet.merge_range(0, 0, 0, 10, 'Inventory Ageing Report', title)
        sheet.write(1, 0, 'Receiving Date', title1)
        sheet.write(1, 1, 'Location', title1)
        sheet.write(1, 2, 'Item Category', title1)
        sheet.write(1, 3, 'Item Code', title1)
        sheet.write(1, 4, 'Season', title1)
        sheet.write(1, 5, 'Short Desc', title1)
        sheet.write(1, 6, 'Color', title1)
        sheet.write(1, 7, 'Size', title1)
        sheet.write(1, 8, 'On Hand Stock', title1)
        sheet.write(1, 9, 'No. Of Days', title1)
        sheet.write(1, 10, 'UOM', title1)
        if data['data']['location_id']:
            domain = []
            if data['data']['location_id']:
                domain.append(('location_id', '=', data['data']['location_id']))
            stock_ageing = self.env['stock.move.line'].sudo().search(domain)
            row = 1
            for i in stock_ageing:
                if i.qty_done > 0:
                    product_name = i.product_id.display_name
                    date_str =data['data']['date_from']
                    h =  datetime.strptime(date_str, '%Y-%m-%d')
                    no_days = h.date() - i.date.date()
                    row += 1
                    sheet.write(row, 0, str(i.date), title2)
                    sheet.write(row, 1, i.location_id.display_name, title2)
                    sheet.write(row, 2, i.product_id.categ_id.display_name, title2)
                    sheet.write(row, 3, i.product_id.name, title2)
                    sheet.write(row, 4, i.product_id.season if i.product_id.season else '-', title2)
                    sheet.write(row, 5, i.product_id.display_name, title2)
                    sheet.write(row, 6, '-', title2)
                    sheet.write(row, 7, '-', title2)
                    sheet.write(row, 8, i.qty_done, title2)
                    sheet.write(row, 9, abs(no_days.days), title2)
                    sheet.write(row, 10, i.product_uom_id.name, title2)
        else:
            domain = []
            domain.append(('location_id.usage', '=', 'internal'))
            stock_ageing = self.env['stock.move.line'].sudo().search(domain)
            row = 1
            for i in stock_ageing:
                if i.qty_done > 0:
                    product_name = i.product_id.display_name
                    date_str = data['data']['date_from']
                    h = datetime.strptime(date_str, '%Y-%m-%d')
                    no_days = h.date() - i.date.date()
                    row += 1
                    sheet.write(row, 0, str(i.date), title2)
                    sheet.write(row, 1, i.location_id.display_name, title2)
                    sheet.write(row, 2, i.product_id.categ_id.display_name, title2)
                    sheet.write(row, 3, i.product_id.name, title2)
                    sheet.write(row, 4, i.product_id.season if i.product_id.season else '-', title2)
                    sheet.write(row, 5, i.product_id.display_name, title2)
                    sheet.write(row, 6, '-', title2)
                    sheet.write(row, 7, '-', title2)
                    sheet.write(row, 8, i.qty_done, title2)
                    sheet.write(row, 9, abs(no_days.days), title2)
                    sheet.write(row, 10, i.product_uom_id.name, title2)
