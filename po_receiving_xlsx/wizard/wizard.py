from odoo import fields, models


class XlsxSaleReports(models.TransientModel):
    _name = 'po.receiving.wizard'
    _description = 'PO Receiving Report'

    date_from = fields.Date('Date from', default=fields.Datetime.now())
    date_to = fields.Date('Date to', default=fields.Datetime.now())
    vendor_ids = fields.Many2many('res.partner', string='Vendors')

    def get_print_data(self):
        data = {
            "date_from": self.date_from,
            "date_to": self.date_to,
            'vendors': self.vendor_ids.ids
        }
        active_ids = self.env.context.get('active_ids', [])
        datas = {
            'ids': active_ids,
            'model': 'reports.xlsx',
            'data': data
        }
        return self.env.ref('po_receiving_xlsx.po_receiving_report_id').report_action([], data=datas)


class PartnerXlsx(models.AbstractModel):
    _name = "report.po_receiving_xlsx.po_receiving_report"
    _inherit = "report.report_xlsx.abstract"
    _description = "PO Receiving Report"

    def get_tax(self, line=None):
        line_tax = 0
        for tax in line.tax_ids:
            line_tax += line.price_subtotal * (tax.amount / 100)
        return line_tax

    def get_gender(self, product=None):
        gender = None
        if product.name.split('-')[0].upper() == 'M':
            gender = 'Men'
        elif product.name.split('-')[0].upper() == 'W':
            gender = 'Women'
        else:
            gender = None
        return gender

    def get_class(self, product_template=None):
        cls = None
        if product_template.x_studio_open_class:
            cls = "Open"
        elif product_template.x_studio_close_class:
            cls = 'Close'
        else:
            cls = None
        return cls

    def get_assortment_size_range(self, product=None):
        size_range = []
        assortment = []
        for rec in product:
            if rec.sh_bundle_product_ids:
                for assort in rec.sh_bundle_product_ids:
                    assortment.append(int(assort.sh_qty))
                for size in rec.sh_bundle_product_ids:
                    product_attribute = size.sh_product_id.product_template_attribute_value_ids
                    size = product_attribute.filtered(
                        lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                    )
                    size_range.append(size.name)
                assortment = '-'.join([str(assortment[i]) for i in range(len(assortment))])
                # size_range = min(size_range) + '-' + max(size_range) if size_range else size_range
                size_range = []
                # return '(' + size_range + ')', '(' + assortment + ')'
                return size_range, '(' + assortment + ')'
            else:
                return size_range, assortment

    def get_product_related_pickings(self, purchase=None, product=None):
        query = f"""select sml.product_id,sml.qty_done,sml.create_date from stock_move_line sml left join 
        stock_picking sp on sml.picking_id = sp.id where sp.origin='{purchase.name}' and sml.product_id = {product.id}"""
        res = self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        new_res = []
        for rec in res:
            dict_exist = next(
                (item for item in new_res if item['create_date'].date() ==
                 rec['create_date'].date()), None)
            if dict_exist:
                dict_exist['qty_done'] += rec['qty_done']
            else:
                new_res.append(rec)
        return new_res

    def get_merge_qty(self, purchase_order=None, product_id=None):
        merge_dic = []
        total_qty = 0
        total_received = 0
        for p in purchase_order:
            for l in p.order_line:
                if l.product_id.id == product_id.id:
                    dict_exist = next(
                        (item for item in merge_dic if item['product_id'] == l['product_id']), None)
                    if dict_exist:
                        total_qty += dict_exist['product_qty']
                        total_received += dict_exist['qty_received']
                    else:
                        total_qty += l.product_qty
                        total_received += l.qty_received
        return total_qty, total_received

    def generate_xlsx_report(self, workbook, data, docs):
        domain = [('state', '=', 'done')]
        if data['data']['vendors']:
            domain.append(('partner_id.id', 'in', data['data']['vendors']))
        if data['data']['date_from']:
            domain.append(('date_order', '>=', data['data']['date_from']))
        if data['data']['date_to']:
            domain.append(('date_order', '<=', data['data']['date_to']))
        purchase_orders = self.env['purchase.order'].sudo().search(domain)
        sheet = workbook.add_worksheet('PO Receiving Report')
        bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#fffbed', 'border': True})
        style0 = workbook.add_format({'align': 'left', 'border': True})
        title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 20, 'bg_color': '#D2EC44',
             'border': True})
        header_row_style = workbook.add_format(
            {'bold': True, 'align': 'center', 'border': True, 'valign': 'vcenter', 'bg_color': '#03bafc'})
        num_fmt = workbook.add_format({'num_format': '#,####', 'align': 'left', 'border': True})
        row = 0
        col = 0
        extra_col = 0
        sheet.merge_range(row + 6, col + 21, row + 7, col + 22, 'Purchase Order', header_row_style)
        sheet.set_column(23, 24, 10)
        sheet.merge_range(row + 6, col + 23, row + 7, col + 24, 'Receiving till date', header_row_style)
        sheet.merge_range(row + 6, col + 25, row + 7, col + 26, 'Balance', header_row_style)
        row += 8
        # Header row
        sheet.set_column(0, 5, 18)
        sheet.merge_range(row, col, row + 1, col, 'Gender', header_row_style)
        sheet.merge_range(row, col + 1, row + 1, col + 1, 'Department', header_row_style)
        sheet.merge_range(row, col + 2, row + 1, col + 2, 'Class', header_row_style)
        sheet.merge_range(row, col + 3, row + 1, col + 3, 'Sub Class', header_row_style)
        sheet.merge_range(row, col + 4, row + 1, col + 4, 'Type', header_row_style)
        sheet.merge_range(row, col + 5, row + 1, col + 5, 'Project Name', header_row_style)
        sheet.set_column(6, 7, 10)
        sheet.merge_range(row, col + 6, row + 1, col + 7, 'Articles', header_row_style)
        sheet.set_column(7, 8, 15)
        sheet.merge_range(row, col + 8, row + 1, col + 8, 'Colors', header_row_style)
        sheet.merge_range(row, col + 9, row + 1, col + 10, 'Cost', header_row_style)
        sheet.merge_range(row, col + 11, row + 1, col + 12, 'Retail', header_row_style)
        sheet.merge_range(row, col + 13, row + 1, col + 14, 'Assortment', header_row_style)
        sheet.merge_range(row, col + 15, row + 1, col + 16, 'PO #', header_row_style)
        sheet.merge_range(row, col + 17, row + 1, col + 18, 'PO Create Date', header_row_style)
        sheet.merge_range(row, col + 19, row + 1, col + 20, 'PO Closing Date', header_row_style)
        sheet.merge_range(row, col + 21, row + 1, col + 21, 'Prs', header_row_style)
        sheet.merge_range(row, col + 22, row + 1, col + 22, 'Val', header_row_style)
        sheet.merge_range(row, col + 23, row + 1, col + 23, 'Prs', header_row_style)
        sheet.merge_range(row, col + 24, row + 1, col + 24, 'Val', header_row_style)
        sheet.merge_range(row, col + 25, row + 1, col + 25, 'Prs', header_row_style)
        sheet.merge_range(row, col + 26, row + 1, col + 26, 'Val', header_row_style)
        row += 2
        col = 0
        count = 1
        grand_total = 0
        check_col = []
        d_wise_col = 27
        heading_row = 6
        # putting data started from here
        for ret in purchase_orders:
            done_ids = []
            for line in ret.order_line:
                if line.product_id.id not in done_ids:
                    total_qty, total_received = self.get_merge_qty(ret, line.product_id)
                    product_related_pickings = self.get_product_related_pickings(ret, line.product_id)
                    gender = self.get_gender(line.product_id)
                    size_range, assortment = self.get_assortment_size_range(line.product_id)
                    # line_tax = self.get_tax(line) if line.tax_ids else 0
                    product_attribute = line.product_id.product_template_attribute_value_ids
                    color_id = product_attribute.filtered(
                        lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                    )
                    size = product_attribute.filtered(
                        lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                    )
                    p_temp = self.env['product.template'].search(
                        [('id', '=', line.product_id.product_tmpl_id.id)])
                    p_class = self.get_class(p_temp)
                    addr = ret.partner_id.city

                    # ==> Putting data in body <==
                    sheet.write(row, col, gender, style0)
                    sheet.write(row, col + 1,
                                line.product_id.categ_id.complete_name.split('/')[
                                    -1] if line.product_id.categ_id else '-',
                                style0)
                    sheet.write(row, col + 2, p_class, style0)
                    sheet.write(row, col + 3, p_temp.x_studio_sub_class if p_temp.x_studio_sub_class else None,
                                style0)
                    sheet.write(row, col + 4, p_temp.x_studio_type if p_temp.x_studio_type else None, style0)
                    sheet.write(row, col + 5,
                                p_temp.x_studio_project_name if p_temp.x_studio_project_name else None,
                                style0)
                    sheet.merge_range(row, col + 6, row, col + 7, line.product_id.name, style0)
                    sheet.write(row, col + 8, color_id.name, style0)
                    sheet.merge_range(row, col + 9, row, col + 10, line.product_id.standard_price,
                                      num_fmt)
                    sheet.merge_range(row, col + 11, row, col + 12, line.product_id.list_price, style0)
                    sheet.merge_range(row, col + 13, row, col + 14, assortment if assortment else None, style0)
                    sheet.merge_range(row, col + 15, row, col + 16, ret.name if ret else None, style0)
                    sheet.merge_range(row, col + 17, row, col + 18,
                                      str(ret.date_order.date()) if ret.date_order else None, style0)
                    sheet.merge_range(row, col + 19, row, col + 20,
                                      str(ret.date_approve.date()) if ret.date_approve else None, style0)
                    sheet.write(row, col + 21, total_qty, style0)
                    sheet.write(row, col + 22, total_qty * line.price_unit, style0)
                    sheet.write(row, col + 23, total_received, style0)
                    sheet.write(row, col + 24, total_received * line.price_unit, style0)
                    bal = total_qty - total_received
                    sheet.write(row, col + 25, bal, style0)
                    sheet.write(row, col + 26, bal * line.price_unit, style0)
                    for each in product_related_pickings:
                        dict_exist = next(
                            (item for item in check_col if item['date'].date() == each['create_date'].date()), None)
                        if dict_exist:
                            sheet.write(row, dict_exist['col'], each['qty_done'], style0)
                        else:
                            sheet.set_column(d_wise_col, d_wise_col, 15)
                            sheet.merge_range(heading_row, d_wise_col, heading_row + 1, d_wise_col,
                                              str(each['create_date'].date()), header_row_style)
                            sheet.merge_range(heading_row + 2, d_wise_col, heading_row + 3, d_wise_col, 'Prs',
                                              header_row_style)
                            sheet.write(row, d_wise_col, each['qty_done'], style0)
                            check_col.append({'date': each['create_date'], 'col': d_wise_col})
                            d_wise_col += 1
                            extra_col += 1
                    grand_total += 1
                    row += 1
                    count += 1
                    done_ids.append(line.product_id.id)

        # Top heading
        sheet.merge_range(0, 0, 3, 26 + extra_col, 'PO Receiving Report', title)
        sheet.merge_range(4, 27, 5, 26 + extra_col, 'Date wise Receiving', header_row_style)
        # sheet.merge_range(row, col + 17, row + 1, col + 18, 'Grand Total', header_row_style)
        # sheet.merge_range(row, col + 19, row + 1, col + 20, grand_total, num_fmt)
