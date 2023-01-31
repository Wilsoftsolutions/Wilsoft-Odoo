# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import EbizChargeAPI
import logging
_logger = logging.getLogger(__name__)
from io import BytesIO
import base64
import xlwt
from xlwt import easyxf


def export_generic_method_saleorder(sheet_name, columns):
    header_style = easyxf('font:height 200;pattern: pattern solid, fore_color gray25;'
                          'align: horiz center;font: color black; font:bold True;'
                          "borders: top thin,left thin,right thin,bottom thin")

    text_center = easyxf('font:height 200; align: horiz center;' "borders: top thin,bottom thin")

    workbook = xlwt.Workbook()
    worksheet = []
    worksheet.append(0)

    worksheet[0] = workbook.add_sheet(sheet_name)

    for j in range(len(columns)):
        worksheet[0].write(3, j + 1, columns[j], header_style)
        worksheet[0].col(j).width = 256 * 20

    return worksheet, workbook, header_style, text_center


class UploadSaleOrders(models.Model):
    _name = 'upload.sale.orders'

    add_filter = fields.Boolean(string='Filters')
    transaction_history_line = fields.One2many('list.of.orders', 'sync_transaction_id', string=" ", copy=True,)

    def domain_users(self):
        return [('user_id', '=', self.env.user.id)]

    logs_line = fields.One2many('logs.of.orders', 'sync_log_id', string=" ", copy=True, domain=lambda self: self.domain_users())

    def create_default_records(self):
        list_of_orders = self.env['sale.order'].search([])
        list_of_upload_orders = self.env['list.of.orders'].search([])
        if (len(list_of_orders)) != (len(list_of_upload_orders)):
            list_of_dict = []
            for order in list_of_orders:
                is_order = self.env['list.of.orders'].search([('order_id', '=', order.id)])
                if not is_order:
                    list_of_dict.append({
                        'order_no': order.id,
                        'customer_name': order.partner_id.id,
                        'customer_id': str(order.partner_id.id),
                        "currency_id": self.env.user.currency_id.id,
                        'sync_transaction_id': self.id,
                    })
            if list_of_dict:
                self.env['list.of.orders'].create(list_of_dict)

    def read(self, fields):
        self.create_default_records()

        # self.env["logs.of.customers"].search([('user_id', '=', self.env.user.id)]).unlink()

        resp = super(UploadSaleOrders, self).read(fields)
        return resp

    def upload_orders(self,  *args, **kwargs):
        try:

            filter_record = self.env['list.of.orders'].browse(kwargs['values']).exists()
            if not filter_record:
                raise UserError('Please select a record first!')
            else:
                list_ids = []
                for record in filter_record:
                    list_ids.append(record.order_id)

                return record.order_no.sync_multi_customers_from_upload_saleorders(list_ids)

        except Exception as e:
            raise ValidationError(e)

    def export_orders(self,  *args, **kwargs):
        filter_record = self.env['list.of.orders'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Order Number', 'Customer', 'Customer ID', 'Order Total', 'Balance Remaining', 'Order Date',
                        'Upload Date & Time', 'Upload Status']

        worksheet, workbook, header_style, text_center = export_generic_method_saleorder(sheet_name='Sales Orders',
                                                                               columns=column_names)
        i = 4
        for record in filter_record:
            worksheet[0].write(i, 1, record.order_no.name or '', text_center)
            worksheet[0].write(i, 2, record.customer_name.name or '', text_center)
            worksheet[0].write(i, 3, record.customer_id or '', text_center)
            worksheet[0].write(i, 4, record.amount_total or '', text_center)
            worksheet[0].write(i, 5, record.amount_due or 0, text_center)
            worksheet[0].write(i, 6, str(record.order_date) or '', text_center)
            worksheet[0].write(i, 7, str(record.last_sync_date) or '', text_center)
            worksheet[0].write(i, 8, record.sync_status or '', text_center)
            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': 'Sales Orders.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Sales Orders.xls' % (
                export_id.id),
            'target': 'new', }

    def export_logs(self,  *args, **kwargs):
        filter_record = self.env['logs.of.orders'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Order Number', 'Customer', 'Customer ID', 'Order Total', 'Balance Remaining',
                        'Order Date', 'Upload Date & Time', 'Upload Status']

        worksheet, workbook, header_style, text_center = export_generic_method_saleorder(sheet_name='SalesOrders Logs',
                                                                               columns=column_names)
        i = 4
        for record in filter_record:
            worksheet[0].write(i, 1, record.order_no.name or '', text_center)
            worksheet[0].write(i, 2, record.customer_name.name or '', text_center)
            worksheet[0].write(i, 3, record.customer_id or '', text_center)
            worksheet[0].write(i, 4, record.amount_total or '', text_center)
            worksheet[0].write(i, 5, record.amount_due or 0, text_center)
            worksheet[0].write(i, 6, str(record.order_date) or '', text_center)
            worksheet[0].write(i, 7, str(record.last_sync_date) or '', text_center)
            worksheet[0].write(i, 8, record.sync_status or '', text_center)

            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': 'SalesOrders Logs.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=SalesOrders Logs.xls' % (
                export_id.id),
            'target': 'new', }

    def clear_logs(self, *args, **kwargs):
        filter_record = self.env['logs.of.orders'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_records = []
            for record in filter_record:
                list_of_records.append(record.id)

            text = f"Are you sure you want to clear {len(kwargs['values'])} sales order(s) from the Log?"
            wizard = self.env['wizard.delete.upload.logs'].create({"record_id": self.id,
                                                                   "record_model": 'sales order',
                                                                   "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_upload_logs').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                list_of_records=list_of_records,
                model='logs.of.orders',
            )

            return action


class ListOfOrders(models.Model):
    _name = 'list.of.orders'
    _order = 'create_date desc'

    sync_transaction_id = fields.Many2one('upload.sale.orders', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    order_no = fields.Many2one('sale.order', string='Order Number')
    order_id = fields.Integer(string='Order Number', related="order_no.id")
    customer_name = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    amount_total = fields.Monetary(string='Order Total', related='order_no.amount_total')
    amount_due = fields.Monetary(string='Balance Remaining', related='order_no.amount_due_custom')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)
    order_date = fields.Datetime('Order Date', related='order_no.date_order')
    sync_status = fields.Char(string='Sync Status', related='order_no.sync_response')
    last_sync_date = fields.Datetime(string="Upload Date & Time", related='order_no.last_sync_date')


class LogsOfOrders(models.Model):
    _name = 'logs.of.orders'
    _order = 'last_sync_date desc'

    sync_log_id = fields.Many2one('upload.sale.orders', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    order_no = fields.Many2one('sale.order', string='Order Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    amount_total = fields.Monetary(string='Order Total')
    amount_due = fields.Monetary(string='Balance Remaining')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)
    order_date = fields.Datetime('Order Date')
    sync_status = fields.Char(string='Upload Status')
    last_sync_date = fields.Datetime(string="Upload Date & Time")

    user_id = fields.Many2one('res.users', 'User')
