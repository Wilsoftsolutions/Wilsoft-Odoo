# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .upload_customers import export_generic_method
import logging
_logger = logging.getLogger(__name__)
from io import BytesIO
import base64


class UploadProducts(models.Model):
    _name = 'upload.products'

    add_filter = fields.Boolean(string='Filters')
    transaction_history_line = fields.One2many('list.of.products', 'sync_transaction_id', string=" ", copy=True, )
    logs_line = fields.One2many('logs.of.products', 'sync_log_id', string=" ", copy=True, )

    def create_default_records(self):
        list_of_products = self.env['product.template'].search([])
        list_of_upload_products = self.env['list.of.products'].search([])
        if (len(list_of_products)) != (len(list_of_upload_products)):
            list_of_dict = []
            for product in list_of_products:
                is_product = self.env['list.of.products'].search([('product_id', '=', product.id)])
                if not is_product:
                    list_of_dict.append({
                        'product_name': product.id,
                        'sync_transaction_id': self.id,
                    })
            if list_of_dict:
                self.env['list.of.products'].create(list_of_dict)

    def read(self, fields):
        self.create_default_records()
        resp = super(UploadProducts, self).read(fields)
        return resp

    def upload_products(self, *args, **kwargs):
        try:
            filter_record = self.env['list.of.products'].browse(kwargs['values']).exists()
            if not filter_record:
                raise UserError('Please select a record first!')
            else:
                odooProducts = self.env['product.template']
                list_ids = []
                for record in filter_record:
                    list_ids.append(record.product_id)
                return odooProducts.add_update_to_ebiz(list_ids)
        except Exception as e:
            raise ValidationError(e)

    def export_products(self, *args, **kwargs):
        filter_record = self.env['list.of.products'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        column_names = ['Product', 'Internal Reference', 'Sales Price', 'Cost', 'Quantity On Hand', 'Type', 'Upload Date & Time', 'Upload Status']

        worksheet, workbook, header_style, text_center = export_generic_method(sheet_name='Products',
                                                                               columns=column_names)
        i = 4
        for record in filter_record:
            worksheet[0].write(i, 1, record.product_name.name or '', text_center)
            worksheet[0].write(i, 2, record.internal_reference or '', text_center)
            worksheet[0].write(i, 3, record.sales_price or '', text_center)
            worksheet[0].write(i, 4, record.cost or 0, text_center)
            worksheet[0].write(i, 5, record.quantity or 0, text_center)
            worksheet[0].write(i, 6, record.type or '', text_center)
            worksheet[0].write(i, 7, str(record.last_sync_date) if record.last_sync_date else '', text_center)
            worksheet[0].write(i, 8, record.sync_status or '', text_center)
            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Products.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Products.xls' % (
                export_id.id),
            'target': 'new', }

    def clear_logs(self, *args, **kwargs):
        filter_record = self.env['logs.of.products'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_records = []
            for record in filter_record:
                list_of_records.append(record.id)

            text = f"Are you sure you want to clear {len(kwargs['values'])} product(s) from the Log?"
            wizard = self.env['wizard.delete.upload.logs'].create({"record_id": self.id,
                                                                   "record_model": 'product',
                                                                   "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_upload_logs').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                list_of_records=list_of_records,
                model='logs.of.products',
            )

            return action

    def export_logs(self, *args, **kwargs):
        filter_record = self.env['logs.of.products'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        column_names = ['Product', 'Internal Reference', 'Sales Price', 'Cost', 'Quantity On Hand', 'Type', 'Upload Date & Time', 'Upload Status']
        worksheet, workbook, header_style, text_center = export_generic_method(sheet_name='Products Logs',
                                                                               columns=column_names)

        i = 4

        for record in filter_record:
            worksheet[0].write(i, 1, record.product_name.name or '', text_center)
            worksheet[0].write(i, 2, record.internal_reference or '', text_center)
            worksheet[0].write(i, 3, record.sales_price or '', text_center)
            worksheet[0].write(i, 4, record.cost or 0, text_center)
            worksheet[0].write(i, 5, record.quantity or 0, text_center)
            worksheet[0].write(i, 6, record.type or '', text_center)
            worksheet[0].write(i, 7, str(record.last_sync_date) if record.last_sync_date else '', text_center)
            worksheet[0].write(i, 8, record.sync_status or '', text_center)
            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Products Logs.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Products Logs.xls' % (
                export_id.id),
            'target': 'new', }


class ListOfProducts(models.Model):
    _name = 'list.of.products'
    _order = 'create_date desc'

    sync_transaction_id = fields.Many2one('upload.products', string='Product Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    product_name = fields.Many2one('product.template', string='Name')
    product_id = fields.Integer(string='Product ID', related='product_name.id')

    internal_reference = fields.Char(string='Internal Reference', related='product_name.default_code')
    sales_price = fields.Float(string='Sales Price', related='product_name.list_price')
    cost = fields.Float('Cost', related='product_name.standard_price')
    quantity = fields.Float('Quantity On Hand', related='product_name.qty_available')
    type = fields.Selection([('consu', 'Consumable'), ('service', 'Service'), ('product', 'Storable Product')], 'Product Type', related='product_name.type')
    ebiz_product_id = fields.Char('EBiz Product Internal ID', related='product_name.ebiz_product_internal_id')
    sync_status = fields.Char(string='Sync Status', related='product_name.sync_status')
    last_sync_date = fields.Datetime(string="Upload Date & Time", related='product_name.last_sync_date')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id,
                                  required=True)


class LogsOfProducts(models.Model):
    _name = 'logs.of.products'
    _order = 'last_sync_date desc'

    sync_log_id = fields.Many2one('upload.products', string='Product Reference', required=True,
                                  ondelete='cascade', index=True, copy=False)
    name = fields.Char(string='Name')
    product_name = fields.Many2one('product.template', string='Name')
    product_id = fields.Integer(string='Product ID', related='product_name.id')
    sales_price = fields.Float(string='Sales Price')
    cost = fields.Float('Cost')
    internal_reference = fields.Char(string='Internal Reference')
    quantity = fields.Float('Quantity On Hand')
    type = fields.Selection([('consu', 'Consumable'), ('service', 'Service'), ('product', 'Storable Product')],
                            'Product Type')
    sync_status = fields.Char(string='Sync Status')
    last_sync_date = fields.Datetime(string="Upload Date & Time")
    currency_id = fields.Many2one('res.currency', 'Currency',
                                   default=lambda self: self.env.user.company_id.currency_id.id,
                                  required=True)
    user_id = fields.Many2one('res.users', 'User')
