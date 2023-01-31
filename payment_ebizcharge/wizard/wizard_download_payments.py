from  odoo import fields, models,api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)
from ..models.ebiz_charge import message_wizard


class DownloadEbizPayment(models.TransientModel):
    _name = 'ebiz.download.payments'
    
    def get_default_from_date(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def get_default_to_date(self):
        today = datetime.now()
        end = today + timedelta(days = 1)
        return end.date()

    def _default_payment_lines(self):
        today = datetime.now()
        end = today + timedelta(days = 1)
        start = self.env['res.config.settings'].get_document_download_start_date()
        return self.get_payments(start, end.date())

    def get_payments(self, start, end):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        params = {
            'securityToken': ebiz._generate_security_json(),
            "fromDateTime": str(start),
            "toDateTime": str(end),
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.GetPayments(**params)
        payment_lines = []

        def ref_date(date):
            if not date:
                return date
            rf_date = date.split('-')
            return f"{rf_date[1]}/{rf_date[2]}/{rf_date[0]}"

        if not payments:
            return payment_lines
        for payment in payments:
            if payment['CustomerId'] != 'False':
                odooCustomer = self.env['res.partner'].browse(int(payment['CustomerId'])).exists()
                if odooCustomer:
                    currency_id = odooCustomer.property_product_pricelist.currency_id.id

                    payment_line = {
                        "payment_type": payment['PaymentType'],
                        "payment_internal_id": payment['PaymentInternalId'],
                        "customer_id": str(payment['CustomerId']),
                        "partner_id": int(payment['CustomerId']),
                        "invoice_number": payment['InvoiceNumber'],
                        "invoice_number_op": payment['InvoiceNumber'],
                        "invoice_internal_id": payment['InvoiceInternalId'],
                        "invoice_date": ref_date(payment['InvoiceDate']),
                        "invoice_due_date": ref_date(payment['InvoiceDueDate']),
                        "po_num": payment['PoNum'],
                        "invoice_amount": float(payment['InvoiceAmount'] or "0"),
                        "currency_id": currency_id,
                        "source": payment['PaymentSourceId'] or "N/A",
                        "amount_due": float(payment['AmountDue'] or "0"),
                        "auth_code": payment['AuthCode'],
                        "ref_num": payment['RefNum'],
                        "payment_method": f"{payment['PaymentMethod']} ending in {payment['Last4']}",
                        "date_paid": ref_date(payment['DatePaid'].split('T')[0]),
                        "paid_amount": float(payment['PaidAmount'] or "0"),
                        "paid_amount_op": payment['PaidAmount'],
                        "type_id": 'Credit' if payment['TypeId'] == 'InvCredit' else payment['TypeId'],
                    }
                    payment_lines.append((0, 0, payment_line))
        return payment_lines

    def domain_users(self):
        return [('create_uid', '=', self.env.user.id)]

    from_date = fields.Date("From Date", required=True, default=get_default_from_date)
    to_date = fields.Date("To Date", required=True, default=get_default_to_date)
    payment_lines = fields.One2many('ebiz.payment.lines', 'wiz_id')
    compute_counter = fields.Integer(compute="_compute_payment_line", store=True)
    name = fields.Char('Name', default="Download Payment")
    transaction_log_lines = fields.Many2many('sync.logs', string=" ", copy=True, domain=lambda self: self.domain_users())

    @api.model
    def create(self, values):
        if 'transaction_log_lines' in values:
            values['transaction_log_lines'] = None
        res = super(DownloadEbizPayment, self).create(values)
        return res

    def fetch_again(self):
        self.payment_lines.unlink()

        if self.from_date and self.to_date:
            if not self.from_date < self.to_date:
                message = 'From Date should be lower than the To date!'
                return message_wizard(message, 'Invalid Date')

        self.compute_payment_lines()

        odooLogs = self.env['sync.logs'].search([])
        if odooLogs:
            self.update({
                'transaction_log_lines': [[6, 0, odooLogs.ids]]
            })

        action = self.env.ref('payment_ebizcharge.action_ebiz_download_payments_form_updated').read()[0]
        action['res_id'] = self.id
        return action

    def _compute_payment_line(self):
        if not self.from_date < self.to_date:
            raise ValidationError('From Date should be lower than the to date')
        self.compute_payment_lines()

    def compute_payment_lines(self):
        payments = self.get_payments(self.from_date, self.to_date)
        payments += self.get_received_email_payments(self.from_date, self.to_date)
        self.payment_lines = payments

    def js_mark_as_applied(self, *args, **kwargs):
        if len(kwargs['values']) == 0:
            raise ValidationError('Please select atleast one payment to proceed with this action.')

        return self.mark_as_applied(kwargs['values'])

    def mark_as_applied(self, js_filter_records):
        selected = js_filter_records
        if not selected:
            raise ValidationError('Please select atleast one payment to proceed with this action.')
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        message_lines = []
        success = 0
        failed = 0
        total = len(selected)
        list_of_invoices = []
        try:
            for item in selected:
                message_record = {
                    'customer_name': item['partner_id']['data']['display_name'],
                    'customer_id': item['partner_id']['data']['id'],
                    'invoice_no': item['invoice_number'],
                    'status': 'Success'
                }
                invoice = self.env['account.move'].search([('name', '=', item['invoice_number_op'])])
                credit = self.env['account.payment'].search([('name', '=', item['invoice_number_op'])])
                list_of_invoices.append(self.create_log_lines(item))
                try:
                    if invoice:
                        invoice.ebiz_create_payment_line(item['paid_amount_op'])
                        if not item['is_email_payment']:
                            resp = ebiz.client.service.MarkPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': item['payment_internal_id'],
                                'invoiceNumber': item['invoice_number'],
                                })
                        else:
                            resp = ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': item['payment_internal_id'],

                            })
                    if credit:
                        resp = ebiz.client.service.MarkPaymentAsApplied(**{
                            'securityToken': ebiz._generate_security_json(),
                            'paymentInternalId': item['payment_internal_id'],
                            'invoiceNumber': item['invoice_number_op'],
                        })
                        credit.action_draft()
                        credit.cancel()
                    success += 1
                    if self.payment_lines:
                        history_line = self.payment_lines.search([('invoice_number_op', '=', item['invoice_number_op'])])
                        self.payment_lines = [[2, history_line.id]]
                except:
                    failed += 1
                    message_record['status'] = 'Failed'

                message_lines.append([0, 0, message_record])

            odooLogs = self.env['sync.logs'].create(list_of_invoices)
            for log in odooLogs:
                self.write({
                    'transaction_log_lines': [[4, log.id]]
                })
            # self.write({
            #     'transaction_log_lines': [[6, 0, odooLogs.ids]]
            # })
            wizard = self.env['download.pyament.message'].create({'name': 'Download', 'lines_ids': message_lines,
            'succeeded': success, 'failed': failed, 'total': total})
            action = self.env.ref('payment_ebizcharge.wizard_ebiz_download_message_action').read()[0]
            action['context'] = self._context
            action['res_id'] = wizard.id
            return action
            
        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def create_log_lines(self, log):
        # print('')
        dict1 = {
            'type_id': log['type_id'],
            'invoice_number': log['invoice_number'],
            'partner_id': int(log['customer_id']),
            # 'customer_id': int(log['customer_id']),
            'customer_id': str(log['customer_id']),
            'date_paid': log['date_paid'],
            'invoice_amount': log['invoice_amount'],
            'paid_amount': log['paid_amount'],
            'amount_due': log['amount_due'],
            'payment_method': log['payment_method'],
            'auth_code': log['auth_code'],
            'ref_num': log['ref_num'],
            'currency_id': self.env.user.currency_id.id,
            'last_sync_date': datetime.now(),
        }
        return dict1

    def get_received_email_payments(self,  start, end):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        params = {
            'securityToken': ebiz._generate_security_json(),
            "fromPaymentRequestDateTime": str(start),
            "toPaymentRequestDateTime": str(end),
            "filters": {'SearchFilter': []},
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**params)
        payment_lines = []

        def ref_date(date):
            if not date:
                return date
            rf_date = date.split('-')
            return f"{rf_date[1]}/{rf_date[2]}/{rf_date[0]}"

        if not payments:
            return payment_lines

        for payment in payments:
            if payment['InvoiceNumber'] in ['PM', "Token"]: continue
            if payment['CustomerId'] != 'False':
                try:
                    odooCustomer = self.env['res.partner'].browse(int(payment['CustomerId'])).exists()
                except:
                    continue
                if odooCustomer:
                    currency_id = odooCustomer.property_product_pricelist.currency_id.id
                    payment_line = {
                        "payment_type": payment['PaymentType'],
                        "payment_internal_id": payment['PaymentInternalId'],
                        "customer_id": str(payment['CustomerId']),
                        "partner_id": int(payment['CustomerId']),
                        "invoice_number": payment['InvoiceNumber'],
                        "invoice_number_op": payment['InvoiceNumber'],
                        "invoice_internal_id": payment['InvoiceInternalId'],
                        "invoice_date": ref_date(payment['InvoiceDate']),
                        "invoice_due_date": ref_date(payment['InvoiceDueDate']),
                        "po_num": payment['PoNum'],
                        "invoice_amount": float(payment['InvoiceAmount'] or "0"),
                        "currency_id": currency_id,
                        "source": payment['PaymentSourceId'] or "N/A",
                        "amount_due": float(payment['AmountDue'] or "0"),
                        "auth_code": payment['AuthCode'],
                        "ref_num": payment['RefNum'],
                        "payment_method": f"{payment['PaymentMethod']} ending in {payment['Last4']}",
                        "date_paid": ref_date(payment['DatePaid'].split('T')[0]),
                        "paid_amount": float(payment['PaidAmount'] or "0"),
                        "paid_amount_op": payment['PaidAmount'],
                        "type_id": 'Email Pay' if payment['TypeId'] == 'EmailForm' else payment['TypeId'],
                        "is_email_payment": True,
                    }
                    payment_lines.append((0, 0, payment_line))
        return payment_lines

    @api.model
    def default_get(self, fields):
        res = super(DownloadEbizPayment, self).default_get(fields)
        if 'name' not in res:
            payments = self.get_payments(res['from_date'], res['to_date'])
            payments += self.get_received_email_payments(res['from_date'], res['to_date'])
            list_of_payments = [(5, 0, 0)]
            if payments:
                for payment in payments:
                    list_of_payments.append(tuple(payment))
                res.update({
                    'payment_lines': list_of_payments
                })

            logs = self.env['sync.logs'].search([])
            list_of_logs = [(5, 0, 0)]
            if logs:
                for log in logs:
                    line = (0, 0, {
                        'type_id': log['type_id'],
                        'invoice_number': log['invoice_number'],
                        'partner_id': int(log['customer_id']),
                        'customer_id': str(log['customer_id']),
                        'date_paid': log['date_paid'],
                        'invoice_amount': log['invoice_amount'],
                        'paid_amount': log['paid_amount'],
                        'amount_due': log['amount_due'],
                        'payment_method': log['payment_method'],
                        'auth_code': log['auth_code'],
                        'ref_num': log['ref_num'],
                        'last_sync_date': log['last_sync_date'],
                        'currency_id': self.env.user.currency_id.id,
                    })
                    list_of_logs.append(line)

                res.update({
                    'transaction_log_lines': list_of_logs,
                })
        return res

    def clear_logs(self, *args, **kwargs):
        # print('clear calls')
        if len(kwargs['values']) == 0:
            raise UserError('Please select a record first!')
        else:
            text = f"Are you sure you want to clear {len(kwargs['values'])} payment(s) from the Log?"
            wizard = self.env['wizard.delete.logs.download'].create({"record_id": self.id,
                                                                       "record_model": self._name,
                                                                       "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_downloads_logs_action').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                self.env.context,
                kwargs_values=kwargs['values'],
            )

            return action

        # for record in kwargs['values']:
        #     record_check = self.env['sync.logs'].search([('invoice_number', '=', record['invoice_number']), ('ref_num', '=', record['ref_num'])])
        #     if record_check:
        #         record_check.unlink()
        #
        # return {}


class EbizPaymentLines(models.TransientModel):
    _name = 'ebiz.payment.lines'

    wiz_id = fields.Many2one('ebiz.download.payments')
    check_box = fields.Boolean('Select')
    payment_internal_id = fields.Char('Payment Internal Id')
    partner_id = fields.Many2one('res.partner', 'Customer')
    # customer_id = fields.Integer('Customer ID')
    customer_id = fields.Char('Customer ID')
    invoice_number = fields.Char('Invoice Number')
    invoice_number_op = fields.Char('Invoice Number')
    invoice_internal_id = fields.Char('Invoice Internal Id')
    invoice_date = fields.Char('Invoice Date')
    invoice_due_date = fields.Char('Invoice Due Date')
    po_num = fields.Char('Po Num')
    so_num = fields.Char('So Num')
    invoice_amount = fields.Float('Invoice Total')
    amount_due = fields.Float('Balance Remaining')
    currency_id = fields.Many2one('res.currency')
    currency = fields.Char(string="Currency")
    auth_code = fields.Char('Auth Code')
    ref_num = fields.Char('Reference Number')
    payment_method = fields.Char('Payment Method')
    date_paid = fields.Char('Date Paid')
    paid_amount = fields.Float('Amount Paid')
    paid_amount_op = fields.Char('Amount Paid')
    type_id = fields.Char('Type')
    payment_type = fields.Char('Payment Type')
    source = fields.Char('Source', default="Odoo")
    is_email_payment = fields.Boolean('Is Email Pay', default = False)


class SyncLogs(models.Model):
    _name = 'sync.logs'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    type_id = fields.Char('Type')
    currency_id = fields.Many2one('res.currency')
    invoice_number = fields.Char('Invoice Number')
    partner_id = fields.Many2one('res.partner', 'Customer')
    # customer_id = fields.Integer('Customer ID')
    customer_id = fields.Char('Customer ID')
    date_paid = fields.Char('Date Paid')
    invoice_amount = fields.Float('Invoice Total')
    paid_amount = fields.Float('Amount Paid')
    amount_due = fields.Float('Balance Remaining')
    payment_method = fields.Char('Payment Method')
    auth_code = fields.Char('Auth Code')
    ref_num = fields.Char('Reference Number')
    last_sync_date = fields.Datetime(string="Import Date & Time")


class BatchProcessMessage(models.TransientModel):
    _name = "download.pyament.message"

    name = fields.Char("Name")
    failed = fields.Integer("Failed")
    succeeded = fields.Integer("Succeeded")
    total = fields.Integer("Total")
    lines_ids = fields.One2many('download.pyament.message.line', 'message_id')


class BatchProcessMessageLines(models.TransientModel):
    _name = "download.pyament.message.line"

    customer_id = fields.Char('Customer ID')
    customer_name = fields.Char('Customer')
    invoice_no = fields.Char('Number')
    status = fields.Char('Status')
    message_id = fields.Many2one('download.pyament.message')