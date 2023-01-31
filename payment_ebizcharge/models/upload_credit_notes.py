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


def export_generic_method_for_credit_notes(sheet_name, columns):
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


class UploadCreditNotes(models.Model):
    _name = 'upload.credit.notes'

    add_filter = fields.Boolean(string='Filters')
    invoice_lines = fields.One2many('list.credit.notes', 'sync_invoice_id', string=" ", copy=True,)
    logs_line = fields.One2many('logs.credit.notes', 'sync_log_id', string=" ", copy=True,)

    def create_default_records(self):
        list_of_invoices = self.env['account.move'].search([("move_type", "=", "out_refund"), ("state", "=", 'posted')])
        list_of_upload_invoice = self.env['list.credit.notes'].search([])
        if (len(list_of_invoices)) != (len(list_of_upload_invoice)):
            list_of_dict = []
            for invoice in list_of_invoices:
                is_order = self.env['list.credit.notes'].search([('invoice', '=', invoice.id)])
                if not is_order:
                    list_of_dict.append({
                        'invoice': invoice.id,
                        'partner_id': invoice.partner_id.id,
                        'customer_id': str(invoice.partner_id.id),
                        "currency_id": self.env.user.currency_id.id,
                        'sync_invoice_id': self.id,
                    })
            if list_of_dict:
                self.env['list.credit.notes'].create(list_of_dict)

    def read(self, fields):
        self.create_default_records()

        resp = super(UploadCreditNotes, self).read(fields)
        return resp

    def upload_invoice(self,  *args, **kwargs):
        try:

            filter_record = self.env['list.credit.notes'].browse(kwargs['values']).exists()
            if not filter_record:
                raise UserError('Please select a record first!')
            else:
                list_ids = []
                for record in filter_record:
                    list_ids.append(record.invoice_id)

                return record.invoice.with_context({'credit': 'credit_notes'}).sync_multi_customers_from_upload_invoices(list_ids)

        except Exception as e:
            raise ValidationError(e)

    def export_orders(self,  *args, **kwargs):
        filter_record = self.env['list.credit.notes'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Number', 'Customer', 'Customer ID', 'Invoice Total', 'Balance Remaining', 'Invoice Date',
                        'Due Date', 'Upload Date & Time', 'Sync Status']

        worksheet, workbook, header_style, text_center = export_generic_method_for_credit_notes(sheet_name='Credit_notes',
                                                                               columns=column_names)
        i = 4

        for record in filter_record:
            worksheet[0].write(i, 1, record.invoice.name or '', text_center)
            worksheet[0].write(i, 2, record.partner_id.name or '', text_center)
            worksheet[0].write(i, 3, record.customer_id or '', text_center)
            worksheet[0].write(i, 4, record.amount_total_signed or '', text_center)
            worksheet[0].write(i, 5, record.amount_residual_signed or 0, text_center)
            worksheet[0].write(i, 6, str(record.invoice_date) if record.invoice_date else '', text_center)
            worksheet[0].write(i, 7, str(record.invoice_date_due) if record.invoice_date_due else  '', text_center)
            worksheet[0].write(i, 8, str(record.last_sync_date) if record.last_sync_date else '', text_center)
            worksheet[0].write(i, 9, record.sync_status or '', text_center)

            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': 'Credit_notes.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Credit_notes.xls' % (
                export_id.id),
            'target': 'new', }

    def export_logs(self,  *args, **kwargs):
        filter_record = self.env['logs.credit.notes'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')

        column_names = ['Number', 'Customer', 'Customer ID', 'Invoice Total', 'Balance Remaining', 'Invoice Date',
                        'Due Date', 'Upload Date & Time', 'Sync Status']

        worksheet, workbook, header_style, text_center = export_generic_method_for_credit_notes(sheet_name='Credit_notes Logs',
                                                                               columns=column_names)
        i = 4

        for record in filter_record:
            worksheet[0].write(i, 1, record.invoice.name or '', text_center)
            worksheet[0].write(i, 2, record.partner_id.name or '', text_center)
            worksheet[0].write(i, 3, record.customer_id or '', text_center)
            worksheet[0].write(i, 4, record.amount_total_signed or '', text_center)
            worksheet[0].write(i, 5, record.amount_residual_signed or 0, text_center)
            worksheet[0].write(i, 6, str(record.invoice_date) or '', text_center)
            worksheet[0].write(i, 7, str(record.invoice_date_due) or '', text_center)
            worksheet[0].write(i, 8, str(record.last_sync_date) or '', text_center)
            worksheet[0].write(i, 9, str(record.sync_status) or '', text_center)

            i = i + 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['bill.excel'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': 'Credit_notes Logs.xls'})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.excel&field=excel_file&download=true&id=%s&filename=Credit_notes Logs.xls' % (
                export_id.id),
            'target': 'new', }

    def clear_logs(self, *args, **kwargs):
        filter_record = self.env['logs.credit.notes'].browse(kwargs['values']).exists()
        if not filter_record:
            raise UserError('Please select a record first!')
        else:
            list_of_records = []
            for record in filter_record:
                list_of_records.append(record.id)

            text = f"Are you sure you want to clear {len(kwargs['values'])} credit note(s) from the Log?"
            wizard = self.env['wizard.delete.upload.logs'].create({"record_id": self.id,
                                                                   "record_model": 'credit note',
                                                                   "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_upload_logs').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                list_of_records=list_of_records,
                model='logs.credit.notes',
            )

            return action


class ListCreditNotes(models.Model):
    _name = 'list.credit.notes'
    _order = 'create_date desc'

    sync_invoice_id = fields.Many2one('upload.credit.notes', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    invoice = fields.Many2one('account.move', string='Number')
    invoice_id = fields.Integer(string='Invoice ID', related='invoice.id')
    state = fields.Char(string='State')
    partner_id = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='partner_id.id')
    customer_id = fields.Char(string='Customer ID')
    amount_total_signed = fields.Monetary(string='Amount Total', related='invoice.amount_total')
    amount_residual_signed = fields.Monetary(string='Balance Remaining', related='invoice.amount_residual')
    amount_untaxed = fields.Monetary(string='Tax Excluded', related='invoice.amount_untaxed_signed')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)
    invoice_date_due = fields.Date('Due Date', related='invoice.invoice_date_due')
    last_sync_date = fields.Datetime('Upload Date & Time', related='invoice.last_sync_date')
    sync_status = fields.Char('Sync Status', related='invoice.sync_response')
    invoice_date = fields.Date('Invoice Date', related='invoice.invoice_date')


class LogCreditNotes(models.Model):
    _name = 'logs.credit.notes'
    _order = 'last_sync_date desc'

    sync_log_id = fields.Many2one('upload.credit.notes', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    invoice = fields.Many2one('account.move', string='Number')
    partner_id = fields.Many2one("res.partner", string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='partner_id.id')
    customer_id = fields.Char(string='Customer ID')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)
    amount_untaxed = fields.Monetary(string='Tax Excluded')
    amount_total_signed = fields.Monetary(string='Invoice Total')
    amount_residual_signed = fields.Monetary(string='Balance Remaining')
    invoice_date_due = fields.Date('Due Date')
    invoice_date = fields.Date('Invoice Date')
    last_sync_date = fields.Datetime('Upload Date & Time')
    sync_status = fields.Char('Sync Status')

