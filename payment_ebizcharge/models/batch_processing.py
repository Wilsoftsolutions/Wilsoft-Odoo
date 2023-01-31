# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, MissingError
from .ebiz_charge import EbizChargeAPI
from datetime import datetime, timedelta
import logging
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class BatchProcessing(models.TransientModel):
    _name = 'batch.processing'

    def _default_get_start(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def _default_get_invoices(self):
        filters = [('payment_state', '!=', 'paid'),
                   ('amount_residual', '>', 0),
                   ('date', '>=', self._default_get_start()),
                   ('date', '<=', self._default_get_end_date())]
        list_of_invoices = self.get_list_of_invoices(filters)
        return list(map(lambda x: [0, 0, x], list_of_invoices))

    def _default_get_end_date(self):
        today = datetime.now() + timedelta(days=1)
        return today.date()

    def domain_users(self):
        return [('create_uid', '=', self.env.user.id)]

    @api.model
    def get_card_type_selection(self):
        icons = self.env['payment.icon'].search([]).read(['name'])
        sel = [(i['name'][0], i['name']) for i in icons]
        return sel

    name = fields.Char(string='Batch Processing', default="Batch Processing")
    start_date = fields.Date(string='From Date', default=_default_get_start)
    end_date = fields.Date(string='To Date', default=_default_get_end_date)
    select_customer = fields.Many2one('res.partner', sting='Select Customer',
                                      domain="[('ebiz_internal_id', '!=', False)]")
    currency_id = fields.Many2one('res.currecny')
    transaction_history_line = fields.One2many('sync.batch.processing', 'sync_transaction_id', string=" ", copy=True)
    transaction_log_lines = fields.Many2many('sync.batch.processed', string=" ", copy=True, domain=lambda self: self.domain_users())
    add_filter = fields.Boolean(string='Filters')
    select_unselect = fields.Boolean(string='Select All')
    send_receipt = fields.Boolean(string='Send receipt to customer')

    @api.onchange('send_receipt')
    def send_receipt_method(self):
        for i in self:
            for line in i.transaction_history_line:
                line.send_receipt = i.send_receipt

    @api.model
    def create(self, values):
        if 'transaction_log_lines' in values:
            values['transaction_log_lines'] = None
        res = super(BatchProcessing, self).create(values)
        return res

    @api.model
    def default_get(self, fields):
        res = super(BatchProcessing, self).default_get(fields)
        if res and 'name' not in res:
            filters = [('payment_state', '!=', 'paid'),
                       ('amount_residual', '>', 0),
                       ('state', '=', 'posted'),
                       ('move_type', '=', 'out_invoice'),
                       ('date', '<=', res['end_date']),
                       ('date', '>=', res['start_date'])]
            invoices = self.get_list_of_invoices(filters)
            list_of_invoices = [(5, 0, 0)]
            if invoices:
                for invoice in invoices:
                    line = (0, 0, invoice)
                    list_of_invoices.append(line)

                res.update({
                    'transaction_history_line': list_of_invoices,
                })

            logs = self.env['sync.batch.processed'].search([])
            list_of_logs = [(5, 0, 0)]
            if logs:
                for log in logs:
                    line = (0, 0, {
                        'name': log['name'],
                        'customer_name': int(log['customer_id']),
                        'customer_id': str(log['customer_id']),
                        'date_paid': log['date_paid'],
                        'currency_id': self.env.user.currency_id.id,
                        'amount_paid': log['amount_paid'],
                        'transaction_status': log['transaction_status'],
                        'email': log['email'],
                        'payment_method': log['payment_method'],
                        'auth_code': log['auth_code'],
                        'trasaction_ref': log['trasaction_ref'],
                    })
                    list_of_logs.append(line)

                res.update({
                    'transaction_log_lines': list_of_logs,
                })

        return res

    def search_transaction(self):
        try:
            if not self.start_date and not self.end_date and not self.select_customer:
                raise UserError('No Option Selected!')

            if self.start_date and self.end_date:
                if not self.start_date < self.end_date:
                    self.env["sync.batch.processing"].search([]).unlink()

                    return message_wizard('From Date should be lower than the To date!', 'Invalid Date')

            invoices = False
            filters = [('payment_state', '!=', 'paid'),
                       ('amount_residual', '>', 0),
                       ('state', '=', 'posted'),
                       ('move_type', '=', 'out_invoice')]

            if self.end_date:
                filters.append(('date', '<=', self.end_date))

            if self.start_date:
                filters.append(('date', '>=', self.start_date))

            if self.select_customer:
                filters.append(('partner_id', '=', self.select_customer.id))

            list_of_invoices = self.get_list_of_invoices(filters)

            odooLogs = self.env['sync.batch.processed'].search([])
            if odooLogs:
                self.update({
                    'transaction_log_lines': [[6, 0, odooLogs.ids]]
                })

            if list_of_invoices:
                list_of_invoices = list(map(lambda x: dict(x, **{'sync_transaction_id': self.id}), list_of_invoices))
                self.env["sync.batch.processing"].search([]).unlink()
                self.env['sync.batch.processing'].create(list_of_invoices)
            else:
                self.env["sync.batch.processing"].search([]).unlink()

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(e)

    def get_list_of_invoices(self, fitlers):
        invoices = self.env['account.move'].search(fitlers)
        list_of_invoices = []

        if invoices:
            for invoice in invoices:
                partner = invoice.partner_id
                default_credit_card = self.ebiz_get_default_payment_methods(partner)
                c_type = ''
                if default_credit_card:
                    card_types = self.get_card_type_selection()
                    card_types = {x[0]: x[1] for x in card_types}
                    if default_credit_card.card_type and default_credit_card.card_type != 'Unknown':
                        c_type = card_types[
                            'D' if default_credit_card.card_type == 'DS' else default_credit_card.card_type]
                    dict1 = {
                        'name': invoice['name'],
                        'customer_name': partner.id,
                        'email': partner.email,
                        'customer_id': str(partner.id),
                        'invoice_id': invoice.id,
                        'invoice_date': invoice.date,
                        'invoice_date_due': invoice.invoice_date_due,
                        'currency_id': invoice.currency_id.id,
                        'sales_person': self.env.user.id,
                        'amount': invoice.amount_total,
                        'amount_residual': invoice.amount_residual,
                        'payment_method': f'{c_type if c_type else "Account"} ending in {default_credit_card.short_name[3:]}',
                        'default_card_id': default_credit_card.id,
                    }
                    list_of_invoices.append(dict1)
        return list_of_invoices

    def ebiz_get_default_payment_methods(self, customer):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            methods = ebiz.client.service.GetCustomerPaymentMethodProfiles(
                **{'securityToken': ebiz._generate_security_json(),
                   'customerToken': customer.ebizcharge_customer_token})
            config = self.env['res.config.settings'].sudo().default_get([])
            get_merchant_data = config.get('merchant_data')
            if not methods:
                return
            for method in methods:
                token = customer.payment_token_ids.filtered(lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)
                if not token and method['SecondarySort'] == '0':
                    if method['MethodType'] == 'cc':
                        customer.create_card_from_ebiz_data(method)
                        return customer.payment_token_ids.filtered(
                            lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)
                    else:
                        if get_merchant_data:
                            customer.create_ach_from_ebiz_data(method)
                            return customer.payment_token_ids.filtered(
                                lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)
                        else:
                            return
                elif token.is_default:
                    if token.token_type == 'credit':
                        return token
                    else:
                        if get_merchant_data:
                            return token
                        else:
                            return

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def checkExpiry(self, token):
        return datetime.strptime(token.card_exp_date, '%m/%Y') < datetime.now()

    def create_log_lines(self, invoices, currentRecord):
        selected_invoice = invoices
        list_of_invoices = []
        for invoice in selected_invoice:
            odooInvoice = self.env['account.move'].browse(int(invoice['invoice_id'])).exists()
            transaction_id = odooInvoice.transaction_ids[0]
            dict1 = {
                "name": invoice['name'],
                "customer_name": odooInvoice.partner_id.id,
                "customer_id": odooInvoice.partner_id.id,
                "date_paid": transaction_id.date,
                "currency_id": invoice['currency_id']['data']['id'],
                "amount_paid": invoice['amount'],
                "transaction_status": 'Success' if str(transaction_id.state) == 'done' else str(transaction_id.state),
                "payment_method": invoice['payment_method'],
                "auth_code": transaction_id.ebiz_auth_code,
                "trasaction_ref": transaction_id.acquirer_reference,
                'email': invoice['email'],
            }
            list_of_invoices.append(dict1)
        odooLogs = self.env['sync.batch.processed'].create(list_of_invoices)
        for log in odooLogs:
            currentRecord.write({
                'transaction_log_lines': [[4, log.id]]
            })

    def process_invoices(self, *args, **kwargs):
        """
            Niaz Implementation:
            Email the receipt to customer, if email receipts tempalates not ther in odoo, it will fetch.
            return: wizard to select the receipt template
        """
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            success = 0
            total_count = len(kwargs['values'])

            if not self:
                odooRecord = self.env['batch.processing'].create({
                    'start_date': self._default_get_start(),
                    'end_date': self._default_get_end_date(),
                })
                self = odooRecord

            message_lines = []
            for record in kwargs['values']:
                search_invoice = self.env['account.move'].browse(int(record['invoice_id']))
                respone = search_invoice.sync_to_ebiz()
                x = search_invoice.ebiz_batch_procssing_reg(record['default_card_id'], record['send_receipt'])
                success += 1 if search_invoice.transaction_ids[0].state == 'done' else 0
                message_lines.append([0, 0, {'customer_id': record['customer_id'],
                                             "customer_name": record['customer_name']['data']['display_name'],
                                             'invoice_no': record['name'],
                                             'status': 'Success' if search_invoice.transaction_ids[0].state == 'done' else search_invoice.transaction_ids[0].state}])
                if self.transaction_history_line:
                    history_line = self.transaction_history_line.search([('invoice_id', '=', record['invoice_id'])])
                    self.transaction_history_line = [[2, history_line.id]]

            self.create_log_lines(kwargs['values'], self)
            # self.search_transaction()
            wizard = self.env['batch.process.message'].create({'name': "Batch Process", 'lines_ids': message_lines,
                                                               'success_count': success,'total': total_count})
            return {
                    'type': 'ir.actions.act_window',
                    'name': _('Batch Process Result'),
                    'res_model': 'batch.process.message',
                    'res_id': wizard.id,
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'context': self._context
                   }

        except MissingError as b:
            self.search_transaction()
            return {'type': 'ir.actions.act_window',
                    'name': _('Record Updated!!!'),
                    'res_model': 'message.wizard',
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'context': {
                        'message': 'There was a change in the record, Invoices refreshed! Please try now',
                    },
                    }

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(e)

    def clear_logs(self, *args, **kwargs):
        if len(kwargs['values']) == 0:
            raise UserError('Please select a record first!')
        list_of_records = []
        for record in kwargs['values']:
            filter_record = self.env['sync.batch.processed'].search(
                [('name', '=', record['name']), ('trasaction_ref', '=', record['trasaction_ref'])])
            if filter_record:
                list_of_records.append(filter_record.id)
        text = f"Are you sure you want to clear {len(kwargs['values'])} invoice(s) from the Log?"
        wizard = self.env['wizard.delete.upload.logs'].create({"record_id": self.id,
                                                               "record_model": 'invoice',
                                                               "text": text})
        action = self.env.ref('payment_ebizcharge.wizard_delete_upload_logs').read()[0]
        action['res_id'] = wizard.id

        action['context'] = dict(
            list_of_records=list_of_records,
            model='sync.batch.processed',
        )
        return action

    def js_flush_customer(self, *args, **kwargs):
        try:
            customers = self.env['res.partner'].browse(list(set(kwargs['customers']))).exists()
            for customer in customers:
                customer.payment_token_ids.filtered(lambda x: x.create_uid == self.env.user).with_context({'donot_sync': True}).unlink()
        except MissingError as b:
            pass


class ListSyncBatch(models.TransientModel):
    _name = 'sync.batch.processing'
    _order = 'date_time asc'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id = fields.Many2one('batch.processing', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    customer_id = fields.Char(string='Customer ID')
    # customer_id = fields.Integer(string='Customer ID', related="customer_name.id")
    invoice_id = fields.Char(string='Invoice ID')
    account_holder = fields.Char(string='Account Holder')
    date_time = fields.Datetime(string='Date Time')
    currency_id = fields.Many2one('res.currecny', string='Company Currency')

    # amount = fields.Monetary(string='Invoice Total', currency_field='currency_id')
    amount = fields.Float(string='Invoice Total')
    amount_residual = fields.Float(string='Balance')
    tax = fields.Char(string='Tax Excluded')
    card_no = fields.Char(string='Card Number')
    status = fields.Char(string='Status')
    email = fields.Char(string='Email')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_date_due = fields.Date(string='Due Date')
    sales_person = fields.Many2one('res.users', string='Sales Person')
    payment_method = fields.Char('Payment Method')
    default_card_id = fields.Integer(string='Default Credit Card ID')
    send_receipt = fields.Boolean(string='Send receipt to customer')

    def viewPaymentMethods(self, *args, **kwargs):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Methods',
            'res_model': 'res.partner',
            'res_id': kwargs['values'],
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'flags': {'mode': 'readonly'},
            'context': {'create': False},
        }


class SyncBatchProcessed(models.Model):
    _name = 'sync.batch.processed'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    # processing_id = fields.Many2one('batch.processing', string='Partner Reference', required=True,
    #                                 ondelete='cascade', index=True, copy=False)
    name = fields.Char(string='Invoice Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    customer_id = fields.Char(string='Customer ID')
    # customer_id = fields.Integer(string='Customer ID')
    date_paid = fields.Datetime(string='Date & Time Paid')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    amount_paid = fields.Float(string='Amount Paid')
    transaction_status = fields.Char(string='Transaction Status')
    email = fields.Char(string='Receipt Sent To (Email)', related='customer_name.email')
    payment_method = fields.Char('Payment Method')
    auth_code = fields.Char('Auth Code')
    trasaction_ref = fields.Char('Reference Number')


class SyncBatchLog(models.TransientModel):
    _name = 'sync.batch.log'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)
    name = fields.Char(string='Invoice Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    customer_id = fields.Char(string='Customer ID')
    date_paid = fields.Datetime(string='Date & Time Paid')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    amount_paid = fields.Float(string='Amount Paid')
    transaction_status = fields.Char(string='Transaction Status')
    email = fields.Char(string='Receipt Sent To (Email)', related='customer_name.email')
    payment_method = fields.Char('Payment Method')
    auth_code = fields.Char('Auth Code')
    trasaction_ref = fields.Char('Reference Number')


class BatchProcessMessage(models.TransientModel):
    _name = "batch.process.message"

    name = fields.Char("Name")
    success_count = fields.Integer("Success Count")
    total = fields.Integer("Total")
    lines_ids = fields.One2many('batch.processing.message.line', 'message_id')


class BatchProcessMessageLines(models.TransientModel):
    _name = "batch.processing.message.line"

    customer_id = fields.Char('Customer ID')
    customer_name = fields.Char('Customer Name')
    invoice_no = fields.Char('Number')
    status = fields.Char('Status')
    message_id = fields.Many2one('batch.process.message')


class BatchProcessingV2(models.TransientModel):
    _name = "ebiz.invoice.batch.processing"


class SendReceipt(models.TransientModel):
    _name = "ebiz.invoice.send.receipt"

    send_receipt = fields.Boolean('Send receipt to customer')

    def proceed(self):
        return self.env['account.move'].browse(self._context.get('move_ids')).process_invoices(self.send_receipt)