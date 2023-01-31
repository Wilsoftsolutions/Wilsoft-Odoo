# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)
import xlwt
from io import BytesIO
import base64
from xlwt import easyxf


def export_generic_method(sheet_name, columns):
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


class UploadCustomers(models.Model):
    _name = 'upload.customers'

    add_filter = fields.Boolean(string='Filters')
    transaction_history_line = fields.One2many('list.of.customers', 'sync_transaction_id', string=" ", copy=True,)

    def domain_users(self):
        return [('user_id', '=', self.env.user.id)]

    logs_line = fields.One2many('logs.of.customers', 'sync_log_id', string=" ", copy=True, domain=lambda self: self.domain_users())

    def create_default_records(self):
        # self.env["list.of.customers"].search([]).unlink()
        list_of_customers = self.env['res.partner'].search([])
        list_of_upload_customers = self.env['list.of.customers'].search([])
        if (len(list_of_customers)) != (len(list_of_upload_customers)):
            list_of_dict = []
            for customer in list_of_customers:
                if customer.customer_rank > 0 and customer.active:
                    is_customer = self.env['list.of.customers'].search([('customer_id', '=', str(customer.id))])
                    if not is_customer:
                        list_of_dict.append({
                            'customer_name': customer.id,
                            'customer_id': str(customer.id),
                            'sync_transaction_id': self.id,
                        })
            if list_of_dict:
                self.env['list.of.customers'].create(list_of_dict)

    def read(self, fields):
        self.create_default_records()
        resp = super(UploadCustomers, self).read(fields)
        return resp

    def upload_customers(self, *args, **kwargs):
        try:
            filter_record = self.env['list.of.customers'].browse(kwargs['values']).exists()
            if not filter_record:
                raise UserError('Please select a record first!')
            else:
                list_ids = []
                for record in filter_record:
                    list_ids.append(int(record.customer_id))
                return record.customer_name.sync_multi_customers_from_upload_customers(list_ids)
        except Exception as e:
            raise ValidationError(e)

    def export_customers(self, *args, **kwargs):
        filter_record = self.env['list.of.customers'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Customer ID #', 'Customer', 'Email', 'Phone', 'Street', 'City', 'Country', 'Upload Date & Time', 'Upload Status']

        worksheet, workbook, header_style, text_center = export_generic_method(sheet_name='Customers',
                                                                               columns=column_names)
        i = 4
        for record in filter_record:
            worksheet[0].write(i, 1, record.customer_id or '', text_center)
            worksheet[0].write(i, 2, record.customer_name.name or '', text_center)
            worksheet[0].write(i, 3, record.email_id or '', text_center)
            worksheet[0].write(i, 4, record.customer_phone or '', text_center)
            worksheet[0].write(i, 5, record.street or '', text_center)
            worksheet[0].write(i, 6, record.customer_city or '', text_center)
            worksheet[0].write(i, 7, record.country.name or '', text_center)
            worksheet[0].write(i, 8, str(record.last_sync_date or ''), text_center)
            worksheet[0].write(i, 9, record.sync_status or '', text_center)
            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Customers.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Customers.xls' % (
                export_id.id),
            'target': 'new', }

    def delete_customers(self, *args, **kwargs):
        filter_record = self.env['list.of.customers'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_customer = []
            list_of_records = []
            for record in filter_record:
                ebiz_customer = self.env['res.partner'].search([('id', '=', record.customer_id)])
                if ebiz_customer.ebiz_internal_id:
                    list_of_customer.append(record.customer_id)
                    list_of_records.append(record.id)

            if list_of_customer:
                text = f"Are you sure you want to deactivate {len(kwargs['values'])} customer(s) in Odoo and EBizCharge Hub?"
                wizard = self.env['wizard.inactive.customers'].create({"record_id": self.id,
                                                                 "record_model": self._name,
                                                                 "text": text})
                action = self.env.ref('payment_ebizcharge.wizard_delete_inactive_customers').read()[0]
                action['res_id'] = wizard.id

                action['context'] = dict(
                    self.env.context,
                    kwargs_values=list_of_customer,
                    list_of_records=list_of_records,
                )
                return action

            else:
                raise UserError('Selected customer(s) must be synced prior to being deactivated.')

    def delete_customers_old(self, *args, **kwargs):
        filter_record = self.env['list.of.customers'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_customer = []
            list_of_records = []
            for record in filter_record:
                ebiz_customer = self.env['res.partner'].search([('id', '=', record.customer_id)])
                if ebiz_customer.ebiz_internal_id:
                    ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                    templates = ebiz.client.service.MarkCustomerAsInactive(**{
                        'securityToken': ebiz._generate_security_json(),
                        'customerInternalId': ebiz_customer.ebiz_internal_id,
                    })
                    list_of_customer.append(record.customer_id)
                    list_of_records.append(record.id)

            if list_of_customer:
                text = f"Do you want to archive {len(kwargs['values'])} customer(s) in odoo as well?"
                wizard = self.env['wizard.inactive.customers'].create({"record_id": self.id,
                                                                 "record_model": self._name,
                                                                 "text": text})
                action = self.env.ref('payment_ebizcharge.wizard_delete_inactive_customers').read()[0]
                action['res_id'] = wizard.id

                action['context'] = dict(
                    self.env.context,
                    kwargs_values=list_of_customer,
                    list_of_records=list_of_records,
                )
                return action

            else:
                return {}

    def clear_logs(self, *args, **kwargs):
        filter_record = self.env['logs.of.customers'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_records = []
            for record in filter_record:
                list_of_records.append(record.id)

            text = f"Are you sure you want to clear {len(kwargs['values'])} customer(s) from the Log?"
            wizard = self.env['wizard.delete.upload.logs'].create({"record_id": self.id,
                                                                          "record_model": 'customer',
                                                                          "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_upload_logs').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                list_of_records=list_of_records,
                model='logs.of.customers',
            )

            return action

    def export_logs(self, *args, **kwargs):
        filter_record = self.env['logs.of.customers'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Customer ID #', 'Customer', 'Email', 'Phone', 'Upload Date & Time', 'Upload Status']
        worksheet, workbook, header_style, text_center = export_generic_method(sheet_name='Customer Logs',
                                                                               columns=column_names)

        i = 4

        for record in filter_record:
            worksheet[0].write(i, 1, record.customer_id or '', text_center)
            worksheet[0].write(i, 2, record.customer_name.name or '', text_center)
            worksheet[0].write(i, 3, record.email_id or '', text_center)
            worksheet[0].write(i, 4, record.customer_phone or '', text_center)
            worksheet[0].write(i, 5, str(record.last_sync_date or ''), text_center)
            worksheet[0].write(i, 6, record.sync_status or '', text_center)
            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Customer Logs.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Customer Logs.xls' % (
                export_id.id),
            'target': 'new', }


class bulk_export_excel(models.TransientModel):
    _name = "bill.excel"

    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('Excel Name', size=64)


class ListOfCustomers(models.Model):
    _name = 'list.of.customers'
    _order = 'create_date desc'

    sync_transaction_id = fields.Many2one('upload.customers', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)
    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    customer_id = fields.Char(string='Customer ID')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    email_id = fields.Char(string='Email', related='customer_name.email')
    customer_phone = fields.Char('Phone', related='customer_name.phone')
    customer_city = fields.Char('City', related='customer_name.city')
    street = fields.Char('Street', related='customer_name.street')
    country = fields.Many2one('res.country', 'Country', related='customer_name.country_id')
    sync_status = fields.Char(string='Sync Status', related='customer_name.sync_response')
    last_sync_date = fields.Datetime(string="Upload Date & Time", related='customer_name.last_sync_date')


class LogsOfCustomers(models.Model):
    _name = 'logs.of.customers'
    _order = 'last_sync_date desc'

    sync_log_id = fields.Many2one('upload.customers', string='Partner Reference', required=True,
                                  ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Customer')
    customer_name = fields.Many2one('res.partner', string='Customer')
    customer_id = fields.Char(string='Customer ID')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    email_id = fields.Char(string='Email')
    customer_phone = fields.Char('Phone')
    sync_status = fields.Char(string='Sync Status')
    last_sync_date = fields.Datetime(string="Upload Date & Time")
    street = fields.Char('Address')
    user_id = fields.Many2one('res.users', 'User')
