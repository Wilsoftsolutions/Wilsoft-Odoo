# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, timedelta
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class PaymentRequestBulkPayment(models.TransientModel):
    _name = 'payment.request.bulk.email'

    def _default_get_start(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def _default_get_end_date(self):
        today = datetime.now()+timedelta(days=1)
        return today.date()

    name = fields.Char(string='Email Pay for Invoices')
    start_date = fields.Date(string='From Date', default=_default_get_start)
    end_date = fields.Date(string='To Date', default=_default_get_end_date)
    select_customer = fields.Many2one('res.partner', sting='Select Customer',
                                      domain="[('ebiz_internal_id', '!=', False)]")

    transaction_history_line = fields.One2many('sync.request.payments.bulk', 'sync_transaction_id', string=" ", copy=True)

    transaction_history_line_pending = fields.One2many('sync.request.payments.bulk.pending', 'sync_transaction_id_pending', string=" ", copy=True)

    transaction_history_line_received = fields.One2many('sync.request.payments.bulk.received', 'sync_transaction_id_received', string=" ", copy=True)

    add_filter = fields.Boolean(string='Filters')

    @api.model
    def default_get(self, fields):
        res = super(PaymentRequestBulkPayment, self).default_get(fields)
        installing_module = self.env.context.get('install_module')
        if res and not installing_module:

            list_of_invoices = [(5, 0, 0)]
            list_of_pending = [(5, 0, 0)]
            list_of_received = [(5, 0, 0)]

            invoices = self.default_invoice(res['start_date'], res['end_date'])
            pending_invoices = self.default_pending_invoice(res['start_date'], res['end_date'])
            recieved_payments = self.default_received_invoices(res['start_date'], res['end_date'])

            if invoices:
                for invoice in invoices:
                    partner = invoice.partner_id

                    dict1 = (0, 0, {
                        # 'sync_date': datetime.now(),
                        'name': invoice['name'],
                        'customer_name': partner.id,
                        'customer_id': str(partner.id),
                        'email_id': partner.email,
                        'invoice_id': invoice.id,
                        'invoice_date': invoice.date,
                        'sales_person': self.env.user.id,
                        'amount': invoice.amount_total,
                        "currency_id": invoice.currency_id.id,
                        'amount_due': invoice.amount_residual_signed,
                        'tax': invoice.amount_untaxed_signed,
                        'invoice_due_date': invoice.invoice_date_due,
                        'sync_transaction_id': self.id,
                    })
                    list_of_invoices.append(dict1)

            if pending_invoices:
                for invoice in pending_invoices:
                    check = True
                    partner = invoice.partner_id
                    if recieved_payments:
                        for invoice_check in recieved_payments:
                            if invoice.payment_internal_id == invoice_check['PaymentInternalId']:
                                check = False

                    if check:
                        date_check = False
                        if invoice.date_time_sent_for_email:
                            date_check = 'due in 3 days' if (
                                    datetime.now() - invoice.date_time_sent_for_email).days <= 3 else '3 days overdue'
                        dict2 = (0, 0, {
                            # 'sync_date': datetime.now(),
                            'name': invoice['name'],
                            'customer_name': partner.id,
                            'customer_id': str(partner.id),
                            'invoice_id': invoice.id,
                            'invoice_date': invoice.date,
                            'email_id': invoice.email_for_pending if invoice.email_for_pending else invoice.partner_id.email,
                            'sales_person': self.env.user.id,
                            'amount': invoice.amount_total,
                            "currency_id": invoice.currency_id.id,
                            'amount_due': invoice.amount_residual_signed,
                            'tax': invoice.amount_untaxed_signed,
                            'date_and_time_Sent': invoice.date_time_sent_for_email or None,
                            'over_due_status': date_check if date_check else None,
                            'invoice_due_date': invoice.invoice_date_due,
                            'sync_transaction_id_pending': self.id,
                            'ebiz_status': 'Pending' if invoice.ebiz_invoice_status == 'pending' else invoice.ebiz_invoice_status,
                            'email_requested_amount': invoice.email_requested_amount,
                            'no_of_times_sent': invoice.no_of_times_sent,
                        })
                        list_of_pending.append(dict2)

            if recieved_payments:
                for portal_invoice in recieved_payments:
                    invoice = self.env['account.move'].search(
                        [('payment_internal_id', '=', portal_invoice['PaymentInternalId']),
                         ('ebiz_invoice_status', '=', 'pending')])
                    if invoice:
                        partner = invoice.partner_id

                        dict3 = (0, 0, {
                            # 'sync_date': datetime.now(),
                            'name': invoice['name'],
                            'customer_name': partner.id,
                            'customer_id': str(partner.id),
                            'invoice_id': invoice.id,
                            'invoice_date': invoice.date,
                            "currency_id": invoice.currency_id.id,
                            'sales_person': self.env.user.id,
                            'amount': float(invoice.amount_total),
                            'amount_due': float(invoice.amount_residual_signed),
                            'paid_amount': float(portal_invoice['PaidAmount']),
                            'email_id': portal_invoice['CustomerEmailAddress'],
                            'ref_num': portal_invoice['RefNum'],
                            'payment_request_date_time': datetime.strptime(portal_invoice['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                            'payment_method': f"{portal_invoice['PaymentMethod']} ending in {portal_invoice['Last4']}",
                            'sync_transaction_id_received': self.id,
                        })
                        list_of_received.append(dict3)

            res.update({
                'transaction_history_line': list_of_invoices,
                'transaction_history_line_pending': list_of_pending,
                'transaction_history_line_received': list_of_received,
            })
        return res

    def default_invoice(self, start_date, end_date):
        return self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                    ('state', '=', 'posted'),
                                                    ('ebiz_invoice_status', '!=', 'pending'),
                                                    ('date', '>=', start_date),
                                                    ('date', '<=', end_date),
                                                    ('amount_residual', '>', 0),
                                                    ('move_type', '!=', 'out_refund'), ])

    def default_pending_invoice(self, start_date, end_date):
        return self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                         ('state', '=', 'posted'),
                                         ('ebiz_invoice_status', '=', 'pending'),
                                         ('ebiz_invoice_status', '!=', 'delete'),
                                         ('date', '>=', start_date),
                                         ('date', '<=', end_date),
                                         ('amount_residual', '>', 0),
                                         ('move_type', '!=', 'out_refund'), ])

    def default_received_invoices(self, start_date, end_date):

        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        dicti = {
            'securityToken': ebiz._generate_security_json(),
            'filters': {'SearchFilter': []},
            'fromPaymentRequestDateTime': start_date,
            'toPaymentRequestDateTime' : end_date,
            'start': 0,
            'limit': 100000,
        }

        return ebiz.client.service.SearchEbizWebFormReceivedPayments(**dicti)

    def search_transaction(self):
        try:
            if not self.start_date and not self.end_date and not self.select_customer:
                self.env["sync.request.payments.bulk"].search([]).unlink()
                self.env["sync.request.payments.bulk.pending"].search([]).unlink()
                self.env["sync.request.payments.bulk.received"].search([]).unlink()
                return message_wizard('No Option Selected!', 'Something Went Wrong')
                # raise UserError('No Option Selected!')

            if self.start_date and self.end_date:
                if not self.start_date < self.end_date:
                    self.env["sync.request.payments.bulk"].search([]).unlink()
                    self.env["sync.request.payments.bulk.pending"].search([]).unlink()
                    self.env["sync.request.payments.bulk.received"].search([]).unlink()
                    return message_wizard('From Date should be lower than the To date!', 'Invalid Date')

            invoices = False
            pending_invoices = False

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            dicti = {
                'securityToken': ebiz._generate_security_json(),
                'filters': {'SearchFilter': []},
                'start': 0,
                'limit': 100000,
            }

            if self.select_customer and self.start_date and self.end_date:
                invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '!=', 'pending'),
                                                            ('date', '>=', self.start_date),
                                                            ('date', '<=', self.end_date),
                                                            ('partner_id', '=', self.select_customer.id),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])

                pending_invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '=', 'pending'),
                                                            ('ebiz_invoice_status', '!=', 'delete'),
                                                            ('date', '>=', self.start_date),
                                                            ('date', '<=', self.end_date),
                                                            ('partner_id', '=', self.select_customer.id),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])

                dicti['fromPaymentRequestDateTime'] = self.start_date
                dicti['toPaymentRequestDateTime'] = self.end_date
                dicti['customerId'] = self.select_customer.id

            elif self.start_date and self.end_date:
                invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '!=', 'pending'),
                                                            ('date', '>=', self.start_date),
                                                            ('date', '<=', self.end_date),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])

                pending_invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '=', 'pending'),
                                                            ('ebiz_invoice_status', '!=', 'delete'),
                                                            ('date', '>=', self.start_date),
                                                            ('date', '<=', self.end_date),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])
                dicti['fromPaymentRequestDateTime'] = self.start_date
                dicti['toPaymentRequestDateTime'] = self.end_date

            elif self.select_customer:
                invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '!=', 'pending'),
                                                            ('partner_id', '=', self.select_customer.id),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])

                pending_invoices = self.env['account.move'].search([('payment_state', '!=', 'paid'),
                                                            ('state', '=', 'posted'),
                                                            ('ebiz_invoice_status', '=', 'pending'),
                                                            ('ebiz_invoice_status', '!=', 'delete'),
                                                            ('partner_id', '=', self.select_customer.id),
                                                            ('amount_residual', '>', 0),
                                                            ('move_type', '!=', 'out_refund'),])

                today = datetime.now()
                end = today + timedelta(days=1)
                start = today + timedelta(days=-365)

                dicti['fromPaymentRequestDateTime'] = str(start.date())
                dicti['toPaymentRequestDateTime'] = str(end.date())

                dicti['customerId'] = self.select_customer.id

            recieved_payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**dicti)

            if invoices or pending_invoices or recieved_payments:
                self.env["sync.request.payments.bulk"].search([]).unlink()
                list_of_trans = []
                if invoices:
                    for invoice in invoices:
                        partner = invoice.partner_id

                        dict1 = {
                            # 'sync_date': datetime.now(),
                            'name': invoice['name'],
                            'customer_name': partner.id,
                            'customer_id': partner.id,
                            'invoice_id': invoice.id,
                            'invoice_date': invoice.date,
                            'sales_person': self.env.user.id,
                            'amount': invoice.amount_total,
                            "currency_id": invoice.currency_id.id,
                            'amount_due': invoice.amount_residual_signed,
                            'tax': invoice.amount_untaxed_signed,
                            'invoice_due_date': invoice.invoice_date_due,
                            # 'payment_method': f'VISA ending in {defualt_credit_card.short_name[3:]}',
                            'sync_transaction_id': self.id,
                            # 'default_card_id': defualt_credit_card.id,
                        }
                        list_of_trans.append(dict1)
                    self.env['sync.request.payments.bulk'].create(list_of_trans)

                if pending_invoices:
                    self.env["sync.request.payments.bulk.pending"].search([]).unlink()
                    list_of_pending_trans = []
                    for invoice in pending_invoices:
                        check = True
                        partner = invoice.partner_id
                        if recieved_payments:
                            for invoice_check in recieved_payments:
                                if invoice.payment_internal_id == invoice_check['PaymentInternalId']:
                                    check = False

                        if check:
                            date_check = False
                            if invoice.date_time_sent_for_email:
                                date_check = 'due in 3 days' if (datetime.now() - invoice.date_time_sent_for_email).days <=3 else '3 days overdue'
                            dict2 = {
                                # 'sync_date': datetime.now(),
                                'name': invoice['name'],
                                'customer_name': partner.id,
                                'customer_id': partner.id,
                                'invoice_id': invoice.id,
                                'invoice_date': invoice.date,
                                'email_id': invoice.email_for_pending if invoice.email_for_pending else invoice.partner_id.email,
                                'sales_person': self.env.user.id,
                                'amount': invoice.amount_total,
                                "currency_id": invoice.currency_id.id,
                                'amount_due': invoice.amount_residual_signed,
                                'tax': invoice.amount_untaxed_signed,
                                'date_and_time_Sent': invoice.date_time_sent_for_email or None,
                                'over_due_status': date_check if date_check else None,
                                'invoice_due_date': invoice.invoice_date_due,
                                # 'payment_method': f'VISA ending in {defualt_credit_card.short_name[3:]}',
                                'sync_transaction_id_pending': self.id,
                                'ebiz_status': 'Pending' if invoice.ebiz_invoice_status == 'pending' else invoice.ebiz_invoice_status,
                                'email_requested_amount': invoice.email_requested_amount,
                                # 'default_card_id': defualt_credit_card.id,
                                'no_of_times_sent': invoice.no_of_times_sent,
                            }
                            list_of_pending_trans.append(dict2)
                    self.env['sync.request.payments.bulk.pending'].create(list_of_pending_trans)

                else:
                    self.env["sync.request.payments.bulk.pending"].search([]).unlink()

                if recieved_payments:
                    self.env["sync.request.payments.bulk.received"].search([]).unlink()
                    list_of_received_trans = []
                    for portal_invoice in recieved_payments:
                        invoice = self.env['account.move'].search([('payment_internal_id', '=', portal_invoice['PaymentInternalId']),
                                                                    ('ebiz_invoice_status', '=', 'pending')])
                        if invoice:
                            partner = invoice.partner_id

                            dict3 = {
                                # 'sync_date': datetime.now(),
                                'name': invoice['name'],
                                'customer_name': partner.id,
                                'customer_id': partner.id,
                                'invoice_id': invoice.id,
                                'invoice_date': invoice.date,
                                "currency_id": invoice.currency_id.id,
                                'sales_person': self.env.user.id,
                                'amount': invoice.amount_total,
                                'amount_due': invoice.amount_residual_signed,
                                'paid_amount': portal_invoice['PaidAmount'],
                                'email_id': portal_invoice['CustomerEmailAddress'],
                                'ref_num': portal_invoice['RefNum'],
                                'payment_request_date_time': datetime.strptime(portal_invoice['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                                # 'tax': invoice.amount_untaxed_signed,
                                # 'invoice_due_date': invoice.invoice_date_due,
                                'payment_method': f"{portal_invoice['PaymentMethod']} ending in {portal_invoice['Last4']}",
                                'sync_transaction_id_received': self.id,
                            }
                            list_of_received_trans.append(dict3)
                    self.env['sync.request.payments.bulk.received'].create(list_of_received_trans)
                else:
                    self.env["sync.request.payments.bulk.received"].search([]).unlink()
            else:
                self.env["sync.request.payments.bulk"].search([]).unlink()
                self.env["sync.request.payments.bulk.pending"].search([]).unlink()
                self.env["sync.request.payments.bulk.received"].search([]).unlink()

        except Exception as e:
            raise ValidationError(e)

    def process_invoices(self, *args, **kwargs):
        """
            Niaz Implementation:
            Email the receipt to customer, if email receipts tempalates not ther in odoo, it will fetch.
            return: wizard to select the receipt template
        """
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            payment_lines = []

            for record in kwargs['values']:
                search_invoice = self.env['account.move'].search([('id', '=', record['invoice_id'])])

                payment_line = {
                    "name": search_invoice.name,
                    "customer_name": search_invoice.partner_id.id,
                    "amount_due": search_invoice.amount_residual_signed,
                    "invoice_id": search_invoice.id,
                    "currency_id": self.env.user.currency_id.id,
                    "email_id": search_invoice.partner_id.email,
                }
                payment_lines.append([0, 0, payment_line])
            wiz = self.env['ebiz.request.payment.bulk'].create({})
            wiz.payment_lines = payment_lines
            action = self.env.ref('payment_ebizcharge.action_ebiz_request_payments_bulk').read()[0]
            action['res_id'] = wiz.id
            return action

        except Exception as e:
            raise ValidationError(e)

    def resend_email(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            resp_lines = []
            success = 0
            failed = 0
            total_count = len(kwargs['values'])

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            for invoice in kwargs['values']:
                odoo_invoice = self.env['account.move'].search([('id', '=', invoice['invoice_id'])])

                resp_line = {}
                resp_line['customer_name'] = resp_line['customer_id'] = odoo_invoice.partner_id.id
                resp_line['number'] = odoo_invoice.id

                form_url = ebiz.client.service.ResendEbizWebFormEmail(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': odoo_invoice.payment_internal_id,
                })

                odoo_invoice.no_of_times_sent += 1
                if self:
                    pending_record = self.transaction_history_line_pending.filtered(lambda r: r.id == invoice['id'])
                    pending_record.no_of_times_sent = odoo_invoice.no_of_times_sent
                resp_line['status'] = 'Success'
                success += 1

                resp_lines.append([0, 0, resp_line])

            else:

                wizard = self.env['wizard.email.pay.message'].create({'name': 'resend_email_pay', 'lines_ids': resp_lines,
                                                                      'success_count': success,
                                                                      'failed_count': failed,
                                                                      'total': total_count})

                return {'type': 'ir.actions.act_window',
                        'name': _('Email Pay for Invoices'),
                        'res_model': 'wizard.email.pay.message',
                        'target': 'new',
                        'res_id': wizard.id,
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'context':
                            self._context,
                        }

        except Exception as e:
            if e.args[0] == 'Error: Object reference not set to an instance of an object.':
                raise UserError('This Invoice Either Paid Or Deleted!')
            raise ValidationError(e)

    def delete_invoice(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            text = f"Are you sure you want to remove {len(kwargs['values'])} request(s) from Pending Requests?"

            wizard = self.env['wizard.delete.email.pay'].create({"record_id": self.id,
                                                                       "record_model": self._name,
                                                                       "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_email_pay_action').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                self.env.context,
                kwargs_values=kwargs['values'],
                pending_recieved='Pending Requests'
            )

            return action

        except Exception as e:
            raise ValidationError(e)

    def delete_invoice_2(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            text = f"Are you sure you want to remove {len(kwargs['values'])} payment(s) from Received Email Payments?"

            wizard = self.env['wizard.delete.email.pay'].create({"record_id": self.id,
                                                                 "record_model": self._name,
                                                                 "text": text})
            action = self.env.ref('payment_ebizcharge.wizard_delete_email_pay_action').read()[0]
            action['res_id'] = wizard.id

            action['context'] = dict(
                self.env.context,
                kwargs_values=kwargs['values'],
                pending_recieved='Received Email Payments'
            )

            return action

        except Exception as e:
            raise ValidationError(e)

    def mark_applied(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            for invoice in kwargs['values']:
                odoo_invoice = self.env['account.move'].search([('id', '=', invoice['invoice_id'])])

                if odoo_invoice:
                    invoice_check = False
                    if odoo_invoice.state != 'posted':
                        super(PaymentRequestBulkPayment, odoo_invoice).action_post()

                    if odoo_invoice['amount_residual'] - float(invoice['paid_amount']) > 0:
                        odoo_invoice.write({
                            'ebiz_invoice_status': 'partially_received',
                            'receipt_ref_num': invoice['ref_num'],
                            'save_payment_link': False,
                            # 'payment_state': 'paid',
                        })
                    else:
                        odoo_invoice.write({
                            'ebiz_invoice_status': 'received',
                            'receipt_ref_num': invoice['ref_num'],
                            'save_payment_link': False,
                            # 'payment_state': 'paid',
                        })

                    reciept_record = self.env['account.move.receipts'].create({
                        'invoice_id': odoo_invoice.id,
                        'name': self.env.user.currency_id.symbol + str(invoice['paid_amount']) + ' Paid On ' +
                                invoice['payment_request_date_time'].split('T')[0],
                        'ref_nums': invoice['ref_num'],
                        'model': '[\'account.move\', \'ebiz.charge.api\']',
                    })

                    journal_id = False
                    payment_acq = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
                    if payment_acq and payment_acq.state == 'enabled':
                        journal_id = payment_acq.journal_id

                    # journal_id = self.env['account.journal'].search([('name', '=', 'Ebiz')])
                    if journal_id:
                        payment = self.env['account.payment'] \
                            .with_context(active_ids=odoo_invoice.ids, active_model='account.move',
                                          active_id=odoo_invoice.id) \
                            .create(
                            {'journal_id': journal_id.id,
                             'payment_method_id': journal_id.inbound_payment_method_ids.id,
                             'amount': float(invoice['paid_amount']),
                             'token_type': None,
                             'partner_id': int(invoice['customer_id']),
                             'ref': invoice['name'] or None,
                             'payment_type': 'inbound'
                             })
                        payment.with_context({'pass_validation': True}).action_post()
                        odoo_invoice.reconcile()
                        odoo_invoice.sync_to_ebiz()
                        if odoo_invoice['amount_residual'] <= 0:
                            # res = super(PaymentRequestBulkPayment, odoo_invoice).payment_action_capture()
                            odoo_invoice.mark_as_applied()
                        else:
                            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                            ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': odoo_invoice.payment_internal_id,

                            })

                            received_payments = self.env['payment.request.bulk.email'].search([])
                            for payment in received_payments:
                                if payment.transaction_history_line_received:
                                    for pending in payment.transaction_history_line_received:
                                        if pending.id == invoice['id']:
                                            payment.transaction_history_line_received = [[2, invoice['id']]]


                            # return res
                    else:
                        raise UserError('EBizCharge Journal Not Found!')

            schedular = self.env['ir.cron'].search([('name', '=', 'Received Payments (Invoice)')]).active
            if invoice_check and not schedular:
                raise UserError(f'The Invoice is not yet paid!')

            return message_wizard('Received payment(s) applied successfully!')

        except Exception as e:
            raise ValidationError(e)

    @api.model
    def load_views(self, views, options=None):
        self.env["sync.request.payments.bulk"].search([]).unlink()
        self.env["sync.request.payments.bulk.pending"].search([]).unlink()
        self.env["sync.request.payments.bulk.received"].search([]).unlink()
        return super(PaymentRequestBulkPayment, self).load_views(views, options=options)


class ListSyncBulkInvoices(models.TransientModel):
    _name = 'sync.request.payments.bulk'
    _order = 'date_time asc'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id = fields.Many2one('payment.request.bulk.email', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    invoice_id = fields.Char(string='Invoice ID')
    account_holder = fields.Char(string='Account Holder')
    date_time = fields.Datetime(string='Date Time')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    amount = fields.Float(string='Invoice Total')
    amount_due = fields.Float(string='Amount Due')
    tax = fields.Float(string='Tax Excluded')
    card_no = fields.Char(string='Card Number')
    status = fields.Char(string='Status')
    email_id = fields.Char(string='Email', related='customer_name.email')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_due_date = fields.Date(string='Due Date')
    sales_person = fields.Many2one('res.users', string='Sales Person')
    payment_method = fields.Char('Payment Method')
    default_card_id = fields.Integer(string='Default Credit Card ID')


class ListPendingBulkInvoices(models.TransientModel):
    _name = 'sync.request.payments.bulk.pending'
    _order = 'date_time asc'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id_pending = fields.Many2one('payment.request.bulk.email', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    invoice_id = fields.Char(string='Invoice ID')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    account_holder = fields.Char(string='Account Holder')
    date_time = fields.Datetime(string='Date Time')
    amount = fields.Float(string='Invoice Total')
    amount_due = fields.Float(string='Amount Due')
    tax = fields.Float(string='Tax Excluded')
    card_no = fields.Char(string='Card Number')
    status = fields.Char(string='Status')
    email_id = fields.Char(string='Email')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_due_date = fields.Date(string='Due Date')
    sales_person = fields.Many2one('res.users', string='Sales Person')
    payment_method = fields.Char('Payment Method')
    ebiz_status = fields.Char('Ebiz Status')
    over_due_status = fields.Char('Status')
    date_and_time_Sent = fields.Datetime('Org. Date & Time Sent')
    email_requested_amount = fields.Float('Requested Amount')
    no_of_times_sent = fields.Integer("# of Times Sent")
    default_card_id = fields.Integer(string='Default Credit Card ID')


class ListReceivedBulkInvoices(models.TransientModel):
    _name = 'sync.request.payments.bulk.received'
    _order = 'date_time asc'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id_received = fields.Many2one('payment.request.bulk.email', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    invoice_id = fields.Char(string='Invoice ID')
    account_holder = fields.Char(string='Account Holder')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    date_time = fields.Datetime(string='Date Time')
    amount = fields.Float(string='Invoice Total')
    amount_due = fields.Float(string='Amount Due')
    tax = fields.Float(string='Tax Excluded')
    card_no = fields.Char(string='Card Number')
    status = fields.Char(string='Status')
    email_id = fields.Char(string='Email ID')
    invoice_date = fields.Date(string='Invoice Date')
    # invoice_due_date = fields.Date(string='Invoice Due Date')
    sales_person = fields.Many2one('res.users', string='Sales Person')
    payment_method = fields.Char('Payment Method')
    paid_amount = fields.Float('Amount Paid')
    ref_num = fields.Char('Reference Number')
    payment_request_date_time = fields.Datetime('Date & Time Paid')
