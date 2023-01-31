# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError,Warning
from datetime import datetime, timedelta
import logging
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):

    _inherit = ['account.move', 'ebiz.charge.api']
    _name = 'account.move'
    
    def _get_default_ebiz_auto_sync(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        return config.get('ebiz_auto_sync_invoice', False)

    def _get_default_ebiz_auto_sync_credit_note(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        return config.get('ebiz_auto_sync_credit_notes', False)

    def _compute_ebiz_auto_sync(self):
        self.ebiz_auto_sync = False

    def _compute_ebiz_auto_sync_credit_note(self):
        self.ebiz_auto_sync_credit_note = False

    def _compute_schedular_auto_check(self):
        schedular = self.env['ir.cron'].search([('name', '=', 'Received Payments (Invoice)')])
        self.auto_received_schedular = schedular.active

    def _compute_receipt_status(self):
        config = self.env['account.move.receipts'].search(
            [('invoice_id', '=', self.id)])
        # , ('model', '=', self._inherit[0])
        self.receipt_status = True if config else False
        
    ebiz_auto_sync = fields.Boolean(compute="_compute_ebiz_auto_sync", default=_get_default_ebiz_auto_sync)
    ebiz_auto_sync_credit_note = fields.Boolean(compute="_compute_ebiz_auto_sync_credit_note", default=_get_default_ebiz_auto_sync_credit_note)
    ebiz_internal_id = fields.Char('EBizCharge Internal Id', copy=False)
    # ebiz_transaction_id = fields.Char('Ebiz Transactions Id')
    ebiz_transaction_id = fields.Many2one('ebiz.charge.transaction')
    done_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_done_transaction_ids',
                                                  string='Authorized Transactions', copy=False, readonly=True)
    is_refund_processed = fields.Boolean(default=False)

    payment_internal_id = fields.Char(string='EBizCharge Email Responce', copy=False)
    ebiz_invoice_status = fields.Selection([
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('partially_received', 'Partially Received'),
        ('delete', 'Deleted'),
        ('applied', 'Applied'),
    ], string='Email Pay Status', readonly=True, copy=False, index=True,)

    auto_received_schedular = fields.Boolean(compute="_compute_schedular_auto_check", default=False)
    receipt_ref_num = fields.Char(string='Receipt RefNum')
    sync_status = fields.Char(string="EBizCharge Upload Status", compute="_compute_sync_status")
    sync_response = fields.Char(string="Sync Status", copy=False)
    last_sync_date = fields.Datetime(string="Upload Date & Time", copy=False)

    receipt_status = fields.Boolean(compute="_compute_receipt_status", default=False)

    credit_note_ids = fields.One2many('account.move', 'reversed_entry_id', 'Credit Notes')
    ebiz_payment_sync_status = fields.Boolean(compute="_compute_payment_sync_status", store=True, default= False)

    date_time_sent_for_email = fields.Datetime('Date & Time Sent')
    customer_id = fields.Char("Customer ID", compute="_compute_customer_id")
    email = fields.Char("Email", compute="_compute_customer_id")
    default_payment_method_name = fields.Char("Payment Method", compute="_compute_customer_id")
    default_payment_method_id = fields.Integer("Email", compute="_compute_customer_id")
    date_filter = fields.Char("Email")

    email_for_pending = fields.Char('Email')
    email_recieved_payments = fields.Boolean('Email Pay Recieved Payments', default=False)
    # upload_invoice_id = fields.Many2one('ebiz.upload.invoice', 'Credit Notes')
    email_requested_amount = fields.Float('Requested Amount')
    no_of_times_sent = fields.Integer('# of Times Sent')

    save_payment_link = fields.Char('Save Payment Link', copy=False)

    def show_ebiz_invoice(self):
        return {'name': 'Go to website',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': f"https://cloudview1.ebizcharge.net/ViewInvoice1.aspx?InvoiceInternalId={self.ebiz_internal_id}"
                }

    def _compute_customer_id(self):
        for inv in self:
            token = inv.partner_id.get_default_token()
            inv.customer_id = inv.partner_id.id
            inv.email = inv.partner_id.email
            inv.default_payment_method_name = token.display_name if token else 'N/A'
            # inv.default_payment_method_name = token.display_name
            inv.default_payment_method_id = token.id if token else 0

    def _compute_sync_status(self):
        for order in self:
            order.sync_status = "Synchronized" if order.ebiz_internal_id else "Pending"

    @api.depends('transaction_ids')
    def _compute_done_transaction_ids(self):
        for trans in self:
            trans.done_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'done')

    def action_post(self):
        ret = super(AccountMove, self).action_post()
        config = self.env['res.config.settings'].default_get([])
        # on posting invoice auto sync invoice
        for invoice in self:
            if invoice.move_type == "out_invoice" and config.get('ebiz_auto_sync_invoice'):
                if self.partner_id.customer_rank > 0:
                    self.sync_to_ebiz()

            if invoice.move_type == "out_refund" and config.get('ebiz_auto_sync_credit_notes'):
                if self.partner_id.customer_rank > 0:
                    self.sync_to_ebiz()
            elif (invoice.move_type == "out_refund" or invoice.move_type == "out_invoice") and invoice.ebiz_internal_id and not self.done_transaction_ids:
                if self.partner_id.customer_rank > 0:
                    self.sync_to_ebiz()
        return ret

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        up_domain = []

        for i,d in enumerate(domain):
            if d[0] == 'partner_id.payment_token_ids.token_type':
                invoices = self.search(up_domain+domain[i+2:])
                invoices.partner_id.ebiz_get_default_payment_methods_for_all()
                up_domain.append(d)
            if d[0] == 'date_filter':
                start = self.env['res.config.settings'].get_start_date(*d[2].split('-'))
                end = datetime.now().date()
                up_domain += ['&', ('date', '<', str(end)), ('date', '>', str(start))]
            else:
                up_domain.append(d)
        res = super(AccountMove, self).search_read(up_domain, fields, offset, limit, order)
        return res

    # @api.model
    # def create(self, values):
    #     """
    #     Kuldeeps' Implementation 
    #     override create methode to automactically sync invoice while creation
    #     """
    #     config = self.env['res.config.settings'].default_get([])
    #     inv = super(AccountMove, self).create(values)
    #     if config.get('ebiz_auto_sync_invoice'):
    #         if inv.partner_id.customer_rank > 0:
    #             inv.sync_to_ebiz()
    #     return inv

    def sync_to_ebiz(self, time_sample=None):
        """
        Kuldeep Implementation
        Sync single Invoice to ebiz Charge
        """

        update_params = {}
        self.ensure_one()
        sale_id = self.invoice_line_ids.sale_line_ids.order_id
        ebiz = self.get_ebiz_charge_obj(sale_id.website_id.id if sale_id and hasattr(sale_id, 'website_id') else None)
        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()
        if self.ebiz_internal_id:
            resp = ebiz.update_invoice(self)
            update_params = {'sync_response': resp['Error'] or resp['Status']}

            logs_dict = {
                'invoice': self.id,
                'partner_id': self.partner_id.id,
                'customer_id': self.partner_id.id,
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'currency_id': self.env.user.currency_id.id,
                'amount_untaxed': self.amount_untaxed_signed,
                'amount_total_signed': self.amount_total,
                'amount_residual_signed': self.amount_residual,
                'invoice_date_due': self.invoice_date_due,
                'invoice_date': self.invoice_date,
                'name': self.name,
            }
            if self.move_type == 'out_refund':
                self.env['logs.credit.notes'].create(logs_dict)
            else:
                self.env['ebiz.log.invoice'].create(logs_dict)

        else:
            resp_search = False
            resp = ebiz.sync_invoice(self)
            if resp['ErrorCode'] == 2:
                resp_search = self.ebiz_search_invoice()

            update_params.update({'ebiz_internal_id': resp['InvoiceInternalId'] or resp_search['InvoiceInternalId'],
                'sync_response': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error']})

            logs_dict = {
                'invoice': self.id,
                'partner_id': self.partner_id.id,
                'customer_id': self.partner_id.id,
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'currency_id': self.env.user.currency_id.id,
                'amount_untaxed': self.amount_untaxed_signed,
                'amount_total_signed': self.amount_total,
                'amount_residual_signed': self.amount_residual,
                'invoice_date_due': self.invoice_date_due,
                'invoice_date': self.invoice_date,
                'name': self.name,

            }

            if self.move_type == 'out_refund':
                self.env['logs.credit.notes'].create(logs_dict)
            else:
                self.env['ebiz.log.invoice'].create(logs_dict)

        # if self.move_type == 'out_refund':
        #     reference_to_upload_invoice = self.env['list.credit.notes'].search([('invoice_id', '=', self.id)])
        # else:
        #     reference_to_upload_invoice = self.env['ebiz.list.invoice'].search([('invoice_id', '=', self.id)])
        #
        # reference_to_upload_invoice.last_sync_date = datetime.now()
        # reference_to_upload_invoice.sync_status = resp['Error'] or resp['Status']

        update_params.update({
            'last_sync_date': fields.Datetime.now()
            })
        self.write(update_params)
        # if resp['ErrorCode'] == 2:
        #     self.sync_to_ebiz()
        return resp

    def batch_process_invoice(self):
        move_ids = self.ids
        action = self.env.ref('payment_ebizcharge.action_invoice_batch_send_receipt').read()[0]

        context = dict(self._context)
        context['move_ids'] = move_ids
        action['context'] = context
        return action

    def process_invoices(self, send_receipt):
        """
            Niaz Implementation:
            Email the receipt to customer, if email receipts tempalates not ther in odoo, it will fetch.
            return: wizard to select the receipt template
        """

        try:
            message_lines = []
            for record in self:
                respone = record.sync_to_ebiz()
                x = record.ebiz_batch_procssing_reg(record.default_payment_method_id, send_receipt)
                message_lines.append([0, 0, {'customer_id': record.customer_id,
                                             "customer_name": record.partner_id.name,
                                             'invoice_no': record.name,
                                             'status': record.transaction_ids.state}])
            self.create_log_lines()
            wizard = self.env['batch.process.message'].create({'name': "Batch Process", 'lines_ids': message_lines})
            action = self.env.ref('payment_ebizcharge.wizard_batch_process_message_action').read()[0]
            action['context'] = self._context
            action['res_id'] = wizard.id
            return action

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(e)

    def create_log_lines(self):
        list_of_invoices = []
        for invoice in self:
            partner = invoice.partner_id
            transaction_id = invoice.transaction_ids[0]
            dict1 = {
                "name": invoice['name'],
                "customer_name": partner.id,
                "customer_id": partner.id,
                "date_paid": transaction_id.date,
                "currency_id": invoice.currency_id.id,
                "amount_paid": invoice.amount_total,
                "transaction_status": transaction_id.state,
                "payment_method": invoice.default_payment_method_name,
                "auth_code": transaction_id.ebiz_auth_code,
                "trasaction_ref": transaction_id.acquirer_reference,
                'email': invoice.email,
            }
            list_of_invoices.append(dict1)
        self.env['sync.batch.log'].search([]).unlink()
        self.env['sync.batch.log'].create(list_of_invoices)

    def sync_to_ebiz_invoice(self):
        if self.move_type == "out_invoice":
            self.sync_to_ebiz()
            return message_wizard('Invoice uploaded successfully!')
        else:
            return False

    def sync_to_ebiz_credit_note(self):
        if self.move_type  == "out_refund":
            self.sync_to_ebiz()
            return message_wizard('Credit Note uploaded successfully!')
        else:
            return False

    def multi_sync_ebiz(self):
        for inv in self:
            if inv.ebiz_internal_id:
                inv.sync_to_ebiz()

    def ebiz_search_invoice(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.SearchInvoices(**{
                'securityTokenCustomer': ebiz._generate_security_json(),
                'customerId': self.partner_id.id,
                'invoiceNumber': self.name,
                'start':0,
                'limit':0,
                'includeItems': False
            })
        if resp:
            return resp[0]
        return resp

    def action_register_payment(self):
        ret = super(AccountMove, self).action_register_payment()
        if self.ebiz_internal_id:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            from_date = datetime.strftime((self.create_date - timedelta(days = 1)), '%Y-%m-%dT%H:%M:%S')
            to_date = datetime.strftime((datetime.now() + timedelta(days = 1)), '%Y-%m-%dT%H:%M:%S')
            params = {
                'securityToken': ebiz._generate_security_json(),
                "fromDateTime": from_date,
                "toDateTime": to_date,
                "customerId": self.partner_id.id,
                "limit": 1000,
                "start": 0,
            }
            payments = ebiz.client.service.GetPayments(**params)
            payments = list(filter(lambda x: x['InvoiceNumber'] == self.name, payments or []))
            if payments:
                for payment in payments:
                    self.ebiz_create_payment_line(payment['PaidAmount'])
                    resp = ebiz.client.service.MarkPaymentAsApplied(**{
                        'securityToken': ebiz._generate_security_json(),
                        'paymentInternalId': payment['PaymentInternalId'],
                        'invoiceNumber': self.name
                        })
                inv_type = 'invoice' if self.move_type == 'out_invoice' else 'credit note'
                return message_wizard(f'This {inv_type} has already been processed on the EBizCharge portal!')
        return ret

    # def js_assign_outstanding_line(self, line_id):
    #     """
    #     overwrite this function to sync invoice when we pay invoice from existing payment
    #     """
    #     res = super(AccountMove, self).js_assign_outstanding_line(line_id)
    #     self.multi_sync_ebiz()
    #     return res

    def ebiz_get_default_payment_methods(self, customer):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            methods = ebiz.client.service.GetCustomerPaymentMethodProfiles(
                **{'securityToken': ebiz._generate_security_json(),
                   'customerToken': customer.ebizcharge_customer_token})
            if not methods:
                return
            for method in methods:
                token = customer.payment_token_ids.filtered(
                    lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)
                if not token:
                    if method['MethodType'] == 'cc':
                        customer.create_card_from_ebiz_data(method)
                        return customer.payment_token_ids.filtered(
                            lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def action_reverse(self):
        if not self.env.context.get('bypass_credit_note_restriction'):
            total_credit_amount = 0

            for notes in self.credit_note_ids:
                total_credit_amount += notes.amount_total

            if self.amount_total <= total_credit_amount:
                context = dict(self._context)
                params = {
                    "invoice_id": self.id,
                    "text": "You have already given the customer credit for the full amount of invoice. Do you want to give more credit to customer against this invoice?"
                }
                wiz = self.env['wizard.credit.note.validate'].create(params)
                action = self.env.ref('payment_ebizcharge.wizard_credit_note_validate_action').read()[0]
                action['res_id'] = wiz.id
                # action['context'] = dict(self._context)
                return action

        action = super(AccountMove, self).action_reverse()
        if self._context.get('active_model') == 'account.move':
            action['context'] = dict(self._context)
        return action

    def run_ebiz_transaction(self, payment_token_id, command, card=None):
        """
        Kuldeep implemented
        run ebiz transaction on the Invoice
        """
        self.ensure_one()
        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()
        if not self.commercial_partner_id.payment_token_ids:
            raise ValidationError("Please enter payment methode profile on the customer.")
        ebiz = self.get_ebiz_charge_obj()
        if self.env.context.get('run_transaction'):
            resp = ebiz.run_full_amount_transaction(self, payment_token_id, command, card)
        else:
            resp =  ebiz.run_customer_transaction(self, payment_token_id, command)
        # sale_order_id = self.invoice_line_ids.sale_line_ids.order_id
        # sale_order_id.transaction_ids = self.transaction_ids
        # resp['invoice_id'] = self.id
        # self.ebiz_transaction_id = self.env['ebiz.charge.transaction'].create_transaction_record(resp)
        return resp

    def payment_action_capture(self):
        # self.invoice_id.action_invoice_register_payment()
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        # if self.state != 'posted':
        #     self.action_post()
        
        
        # payment = self.env['account.payment']\
        #     .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
        #     .create({'journal_id': journal_id.id, 'payment_method_id': journal_id.inbound_payment_method_ids.id})
        # payment.with_context({'pass_validation': True}).post()
        
        for trans in self.authorized_transaction_ids:
            if trans.payment_id:
                trans.payment_id.action_post()
            else:
                trans._post_process_after_done()

        ret = super(AccountMove, self).payment_action_capture()
        # self.sync_to_ebiz()
        return ret

    def payment_action_void(self):
        ret = super(AccountMove, self).payment_action_void()
        reciept_check = self.env['account.move.receipts'].search([('invoice_id','=', self.id)])
        if reciept_check:
            reciept_check[-1].unlink()
        return ret

    def add_payment_lines_to_ebiz_invoice(self):
        pass

    def ebiz_create_payment_line(self, amount):
        # self.invoice_id.action_invoice_register_payment()
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        # self.action_post()
        payment = self.env['account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
            .create({'journal_id': journal_id.id,
                     'payment_method_id': journal_id.inbound_payment_method_ids.id,
                     'token_type': None,
                     'amount': amount,
                     'partner_id': self.partner_id.id,
                     'ref': self.name or None,
                     'payment_type': 'outbound' if self.move_type == 'out_refund' else 'inbound'
                     })

        payment.with_context({'do_not_run_transaction': True}).action_post()
        self.reconcile()
        self.write({'ebiz_invoice_status': 'partially_received' if self.amount_residual else 'received'})
        return super(AccountMove, self).payment_action_capture()
    
    def ebiz_batch_procssing_reg(self, default_card_id, ebiz_send_receipt):
        # self.invoice_id.action_invoice_register_payment()
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        # self.action_post()
        token = self.env['payment.token'].browse(default_card_id)
        payment = self.env['account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
            .create({'journal_id': journal_id.id,
                     'card_id': default_card_id if token.token_type == "credit" else None,
                     'ach_id': default_card_id if token.token_type == "ach" else None,
                     'payment_token_id': default_card_id,
                     'token_type': token.token_type,
                     'amount': self.amount_residual_signed,
                     'transaction_command': 'Sale',
                     'ebiz_send_receipt': ebiz_send_receipt,
                     'ebiz_receipt_emails': self.partner_id.email,
                     'payment_method_id': journal_id.inbound_payment_method_ids.id,
                     'partner_id': self.partner_id.id,
                     'ref': self.name or None,
                     'payment_type': 'inbound'
                })
        payment.with_context({'payment_data': {
                'token_type': token.token_type,
                'card_id': token if token.token_type == "credit" else None,
                'ach_id': token if token.token_type == "ach" else None,
                'card_card_number': payment.card_card_number,
                'security_code': False,
                'ebiz_send_receipt': False,
                'ebiz_receipt_emails': False
        }, 'batch_processing': True}).action_post()
        self.reconcile()
        self.write({'ebiz_invoice_status': 'partially_received' if self.amount_residual else 'received'})
        return super(AccountMove, self).payment_action_capture()

    def process_refund_transaction(self):
        payment_obj = {
            "invoice_id": self.id,
            "partner_id": self.partner_id.id,
            "amount": self.amount_total,
            "is_refund": True,
        }

        transaction_id = self.invoice_line_ids.sale_line_ids.order_id.done_transaction_ids
        payment_obj['ref_num'] = transaction_id.acquirer_reference
        transaction_id.s2s_do_refund(**payment_obj)
        self.process_refund_payment()
        self.is_refund_processed = True
        return True

    def process_credit_transaction(self):
        payment_obj = {
            "invoice_id": self.id,
            "partner_id": self.partner_id.id,
            "amount": self.amount_total,
            "currency_id": self.currency_id.id,
            "method_id": self.reversed_entry_id.done_transaction_ids.payment_token_id.id
        }

        # order = self.invoice_line_ids.sale_line_ids.order_id
        # if not order.amount_total == self.amount_total:
        #     payment_obj['allow_partial_payment'] = True
        # else:
        #     resp = self.process_refund_transaction()
        #     context['message'] = 'Credit transaction sucessfull!'
        #     return self.message_wizard(context)

        wiz = self.env['wizard.process.credit.transaction'].create(payment_obj)
        action = self.env.ref('payment_ebizcharge.action_process_credit_transaction').read()[0]
        action['res_id'] = wiz.id
        return action

    def process_payment(self):
        payment_obj = {
            "invoice_id": self.id,
            "partner_id": self.partner_id.id,
            "amount": self.amount_total,
            "currency_id": self.currency_id.id,
            "card_account_holder_name": self.partner_id.name,
            "card_avs_street": self.partner_id.street,
            "card_avs_zip": self.partner_id.zip,
        }
        wiz = self.env['wizard.order.process.transaction'].create(payment_obj)
        action = self.env.ref('payment_ebizcharge.action_process_ebiz_transaction').read()[0]
        action['res_id'] = wiz.id
        return action

    def process_refund_payment(self):
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        payment_method_id = self.env['account.payment.method'].search([('code','=','electronic')]).id
        payment = self.env['account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id)\
            .create({'journal_id': journal_id.id, 'payment_method_id': payment_method_id})
        payment.with_context({'pass_validation': True}).action_post()

    def ebiz_sync_multiple_invoices(self):
        resp_lines = []
        success = 0
        failed = 0
        total = len(self)
        time = datetime.now()
        set = self.env['ir.config_parameter'].set_param('payment_ebizcharge.time_spam_test_invoices', time)
        time_sample = get = self.env['ir.config_parameter'].get_param('payment_ebizcharge.time_spam_test_invoices')

        for inv in self:
            resp_line = {
                    'customer_name': inv.partner_id.name,
                    'customer_id': inv.partner_id.id,
                    'invoice_number': inv.name
                }
            try:
                resp = inv.sync_to_ebiz(time_sample)
                resp_line['record_message'] = resp['Error'] or resp['Status'] 

            except Exception as e:
                _logger.exception(e)
                resp_line['record_message'] = str(e)

            if resp_line['record_message'] == 'Success' or resp_line['record_message'] =='Record already exists':
                success += 1
            else:
                failed += 1
            resp_lines.append([0, 0, resp_line])

        wizard = self.env['wizard.multi.sync.message'].create({'name':'invoices', 'invoice_lines_ids':resp_lines,
            'success_count': success, 'failed_count': failed, 'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def sync_multi_customers_from_upload_invoices(self, list):
        invoice_records = self.env['account.move'].browse(list).exists()
        resp_lines = []
        success = 0
        failed = 0
        total = len(invoice_records)

        for inv in invoice_records:
            resp_line = {
                    'customer_name': inv.partner_id.name,
                    'customer_id': inv.partner_id.id,
                    'invoice_number': inv.name
                }
            try:
                resp = inv.sync_to_ebiz()
                resp_line['record_message'] = resp['Error'] or resp['Status']

            except Exception as e:
                _logger.exception(e)
                resp_line['record_message'] = str(e)

            if resp_line['record_message'] == 'Success' or resp_line['record_message'] =='Record already exists':
                success += 1
            else:
                failed += 1
            resp_lines.append([0, 0, resp_line])

        if self.env.context.get('credit') == 'credit_notes':
            wizard = self.env['wizard.multi.sync.message'].create({'name': 'credit_notes', 'invoice_lines_ids':resp_lines,
                'success_count': success, 'failed_count': failed, 'total': total})
        else:
            wizard = self.env['wizard.multi.sync.message'].create({'name': 'invoices', 'invoice_lines_ids': resp_lines,
                                                                   'success_count': success, 'failed_count': failed,
                                                                   'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def write(self, values):
        ret = super(AccountMove, self).write(values)
        if self._ebiz_check_invoice_update(values):
            for invoice in self:
                if invoice.ebiz_internal_id and invoice.partner_id.customer_rank > 0:
                    invoice.sync_to_ebiz()
        return ret

    @api.depends('amount_residual')
    def _compute_payment_sync_status(self):
        for inv in self:
            if inv.state == "posted" and inv.amount_residual != inv.amount_total:
                inv.multi_sync_ebiz()

    def email_invoice_ebiz(self):
        """
        Niaz Implementation:
        Call the wizard, use to send email invoice to customer, fetch the email templates incase not present before
        return: Wizard
        """
        try:

            if self.ebiz_invoice_status == 'pending':
                raise UserError(f'An email pay request has already been sent.')

            if self.state != 'posted':
                self.action_post()

            if not self.ebiz_internal_id:
                self.sync_to_ebiz()

            self.env.cr.commit()

            if self.save_payment_link:
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                today = datetime.now()
                end = today + timedelta(days=1)
                start = today + timedelta(days=-365)

                recieved_payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**{
                    'securityToken': ebiz._generate_security_json(),
                    'fromPaymentRequestDateTime': str(start.date()),
                    'toPaymentRequestDateTime': str(end.date()),
                    'start': 0,
                    'limit': 10000,
                })

                if recieved_payments:
                    for invoice in recieved_payments:
                        odoo_invoice = self.env['account.move'].search([('payment_internal_id', '=', invoice['PaymentInternalId'])])
                        try:
                            if odoo_invoice and odoo_invoice.id == self.id:
                                text = f"There is a payment of {self.env.user.company_id.currency_id.symbol}{float(invoice['PaidAmount'])} received on this {self.name}.\nWould you like to apply this payment?"
                                wizard = self.env['wizard.recieve.email.pay'].create({"record_id": self.id,
                                                                                      "odoo_invoice": odoo_invoice.id,
                                                                                      "text": text})
                                action = self.env.ref('payment_ebizcharge.wizard_recieved_email_pay').read()[0]
                                action['res_id'] = wizard.id
                                action['context'] = dict(
                                    invoice=invoice,
                                )
                                return action
                            else:
                                continue
                        except Exception:
                            pass
                    else:
                        text = f"A payment link has been generated previously. The existing link will become invalid if an email pay request is sent.\nAre you sure you want to send an email pay request?"
                        wizard = self.env['wizard.receive.email.payment.link'].create({"record_id": self.id,
                                                                              "odoo_invoice": self.id,
                                                                              "text": text})
                        action = self.env.ref('payment_ebizcharge.wizard_recieved_email_pay_payment_link').read()[0]
                        action['res_id'] = wizard.id
                        action['context'] = dict(
                            invoice=invoice,
                        )
                        return action

            return {'type': 'ir.actions.act_window',
                    'name': _('Email Pay Request'),
                    'res_model': 'email.invoice',
                    'target': 'new',
                    # 'view_id': self.env.ref('payment_ebizcharge.send_email_invoice_wizard').id,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_contacts_to': [[6, 0, [self.partner_id.id]]],
                        'default_record_id': self.id,
                        'default_currency_id': self.currency_id.id,
                        'default_amount': self.amount_residual if self.amount_residual else self.amount_total,
                        'default_model_name': str(self._inherit),
                        'default_email_customer': str(self.partner_id.email),
                        'selection_check': 1,
                    },
                    }

        except Exception as e:
            raise ValidationError(e)

    def resend_email_invoice_ebiz(self):
        """
            Niaz Implementation:
            Use to resend the email invoice
        """
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            form_url = ebiz.client.service.ResendEbizWebFormEmail(**{
                'securityToken': ebiz._generate_security_json(),
                'paymentInternalId': self.payment_internal_id,
            })

            self.no_of_times_sent += 1

            return message_wizard('Email pay request has been successfully resent!')

        except Exception as e:
            if e.args[0] == 'Error: Object reference not set to an instance of an object.':
                raise UserError('This Invoice Either Paid Or Deleted!')
            raise ValidationError(e)

    # def ebiz_add_invoice_payment(self):
    #     try:
    #         if self.ebiz_payment_internal_id:
    #             return True

    #         ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
    #         trans_id = self.transaction_ids.filtered(lambda x: x.state in ['authorized', 'done'])

    #         if not trans_id:
    #             return False

    #         params = {
    #             'securityToken': ebiz._generate_security_json(),
    #             'payment':{
    #                 'CustomerId': self.partner_id.id,
    #                 'InvoicePaymentDetails':{
    #                     'InvoicePaymentDetails':[
    #                         {
    #                         'InvoiceInternalId': self.ebiz_internal_id,
    #                         'PaidAmount': trans_id.amount,
    #                         }
    #                     ]
    #                 },
    #                 'TotalPaidAmount': trans_id.amount,
    #                 'CustNum': self.partner_id.ebizcharge_customer_token,
    #                 'RefNum': trans_id.acquirer_reference,
    #                 'PaymentMethodType': 'CreditCard' if trans_id.payment_token_id.token_type == 'credit' else 'ACH',
    #                 'PaymentMethodId': trans_id.payment_token_id.id,
    #             }
    #         }
    #         resp = ebiz.client.service.AddInvoicePayment(**params)
    #         if resp['StatusCode'] == 1:
    #             self.ebiz_payment_internal_id = resp['PaymentInternalId']
    #             ebiz.client.service.MarkPaymentAsApplied(**{
    #                     'securityToken': ebiz._generate_security_json(),
    #                     'paymentInternalId': self.ebiz_payment_internal_id,
    #                     'invoiceNumber': self.name
    #                     })
    #         return resp
    #     except Exception as e:
    #         _logger.exception(e)
    #         raise ValidationError(str(e))

    def get_pending_invoicess(self):
        """
            Niaz Implementation:
            Get received payments paid via email invoice, change status of email to Received.
        """
        try:

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            today = datetime.now()
            end = today + timedelta(days=1)
            start = today + timedelta(days=-365)

            recieved_payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**{
                'securityToken': ebiz._generate_security_json(),
                'fromPaymentRequestDateTime': str(start.date()),
                'toPaymentRequestDateTime': str(end.date()),
                'start': 0,
                'limit': 10000,
            })
            invoice_check = True

            if recieved_payments:
                for invoice in recieved_payments:

                    try:
                        odoo_invoice = self.env['account.move'].search(
                            [('payment_internal_id', '=', invoice['PaymentInternalId']),
                             ('ebiz_invoice_status', '=', 'pending')])
                        if odoo_invoice:
                            invoice_check = False
                            if odoo_invoice.state != 'posted':
                                odoo_invoice.action_post()

                            if odoo_invoice['amount_residual'] - float(invoice['PaidAmount']) > 0:
                                odoo_invoice.write({
                                    'ebiz_invoice_status': 'partially_received',
                                    'receipt_ref_num': invoice['RefNum'],
                                    # 'payment_state': 'paid',
                                })
                            else:
                                odoo_invoice.write({
                                    'ebiz_invoice_status': 'received',
                                    'receipt_ref_num': invoice['RefNum'],
                                    # 'payment_state': 'paid',
                                })

                            self.env['account.move.receipts'].create({
                                'invoice_id': odoo_invoice.id,
                                'name': self.env.user.currency_id.symbol + invoice['PaidAmount'][:-2] + ' Paid On ' +
                                        invoice['PaymentRequestDateTime'].split('T')[0],
                                'ref_nums': invoice['RefNum'],
                                'model': str(self._inherit),
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
                                     'amount': float(invoice['PaidAmount']),
                                     'token_type': None,
                                     'partner_id': odoo_invoice.partner_id.id,
                                     'ref': odoo_invoice.name or None,
                                     'payment_type': 'inbound'
                                     })
                                payment.with_context({'pass_validation': True}).action_post()
                                odoo_invoice.reconcile()
                                odoo_invoice.sync_to_ebiz()
                                odoo_invoice.save_payment_link = False
                                if odoo_invoice['amount_residual'] <= 0:
                                    res = super(AccountMove, odoo_invoice).payment_action_capture()
                                    odoo_invoice.mark_as_applied()
                                    return res
                                else:
                                    ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                                        'securityToken': ebiz._generate_security_json(),
                                        'paymentInternalId': odoo_invoice.payment_internal_id,

                                    })
                            else:
                                raise UserError('EBizCharge Journal Not Found!')

                    except Exception:
                        continue

                schedular = self.env['ir.cron'].search([('name', '=', 'Received Payments (Invoice)')]).active
                if invoice_check and self:
                    raise UserError(f'The Invoice is not yet paid!')

            other_payments = ebiz.client.service.GetPayments(**{
                'securityToken': ebiz._generate_security_json(),
                'fromDateTime': str(start.date()),
                'toDateTime': str(end.date()),
                'start': 0,
                'limit': 10000,
            })

            if other_payments:
                for pay in other_payments:
                    try:
                        is_odoo_invoice = self.env['account.move'].search(
                            [('ebiz_internal_id', '=', pay['InvoiceInternalId'])])
                        is_credit = self.env['account.payment'].search([('name', '=', pay['InvoiceNumber'])])

                        if is_odoo_invoice:
                            is_odoo_invoice.ebiz_create_payment_line(pay['PaidAmount'])

                            resp = ebiz.client.service.MarkPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': pay['PaymentInternalId'],
                                'invoiceNumber': pay['InvoiceNumber'],
                            })

                            self.env['account.move.receipts'].create({
                                'invoice_id': is_odoo_invoice.id,
                                'name': self.env.user.currency_id.symbol + pay['PaidAmount'][:-2] + ' Paid On ' +
                                        pay['DatePaid'].split('T')[0],
                                'ref_nums': pay['RefNum'],
                                'model': str(self._inherit),
                            })

                        if is_credit:
                            resp = ebiz.client.service.MarkPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': pay['PaymentInternalId'],
                                'invoiceNumber': pay['InvoiceNumber'],
                            })
                            is_credit.action_draft()
                            is_credit.cancel()

                    except Exception:
                        continue

        except Exception as e:
            raise ValidationError(e)

    def recieved_apply_email_after_confirmation(self, invoice):
        try:
            odoo_invoice = self

            if odoo_invoice.state != 'posted':
                odoo_invoice.action_post()

            if odoo_invoice['amount_residual'] - float(invoice['PaidAmount']) > 0:
                odoo_invoice.write({
                    'ebiz_invoice_status': 'partially_received',
                    'receipt_ref_num': invoice['RefNum'],
                    # 'payment_state': 'paid',
                })
            else:
                odoo_invoice.write({
                    'ebiz_invoice_status': 'received',
                    'receipt_ref_num': invoice['RefNum'],
                    # 'payment_state': 'paid',
                })

            self.env['account.move.receipts'].create({
                'invoice_id': odoo_invoice.id,
                'name': self.env.user.currency_id.symbol + invoice['PaidAmount'][:-2] + ' Paid On ' +
                        invoice['PaymentRequestDateTime'].split('T')[0],
                'ref_nums': invoice['RefNum'],
                'model': str(self._inherit),
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
                     'amount': float(invoice['PaidAmount']),
                     'token_type': None,
                     'partner_id': self.partner_id.id,
                     'ref': self.name or None,
                     'payment_type': 'inbound'
                     })
                payment.with_context({'pass_validation': True}).action_post()
                self.reconcile()
                odoo_invoice.sync_to_ebiz()
                odoo_invoice.save_payment_link = False
                if odoo_invoice['amount_residual'] <= 0:
                    res = super(AccountMove, odoo_invoice).payment_action_capture()
                    odoo_invoice.mark_as_applied()
                    return res
                else:
                    ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                    ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                        'securityToken': ebiz._generate_security_json(),
                        'paymentInternalId': odoo_invoice.payment_internal_id,

                    })
            else:
                raise UserError('EBizCharge Journal Not Found!')

        except Exception as e:
            raise ValidationError(e)

    def reconcile(self):
        for invoice_payment in self:
            payments = self.env['account.payment'].sudo().search([('ref', '=', invoice_payment.name)])
            for payment in payments:
                if not payment.is_reconciled and payment.state == 'posted':
                    payment_ref = self.env['account.move.line'].search([('move_name', '=', payment.name)])
                    index = len(payment_ref)-1
                    invoice_payment.js_assign_outstanding_line(payment_ref[index].id)

    def read(self, fields):
        if len(self) ==1 and self.ebiz_invoice_status == 'pending' and self.email_recieved_payments == False:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            today = datetime.now()
            end = today + timedelta(days=1)
            start = today + timedelta(days=-365)

            recieved_payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**{
                'securityToken': ebiz._generate_security_json(),
                'fromPaymentRequestDateTime': str(start.date()),
                'toPaymentRequestDateTime': str(end.date()),
                'start': 0,
                'limit': 10000,
            })
            invoice_check = True

            if recieved_payments:
                for invoice in recieved_payments:
                    odoo_invoice = self.env['account.move'].search(
                        [('payment_internal_id', '=', invoice['PaymentInternalId']),
                         ('ebiz_invoice_status', '=', 'pending')])

                    if odoo_invoice:
                        odoo_invoice.email_recieved_payments = True

        return super(AccountMove, self).read(fields)

    def delete_ebiz_incvoice(self):
        """
            Niaz Implementation:
            Delete the  pending invoice
        """

        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            recieved_payments = ebiz.client.service.DeleteEbizWebFormPayment(**{
                'securityToken': ebiz._generate_security_json(),
                'paymentInternalId': self.payment_internal_id,
            })

            if recieved_payments.Status == 'Success':
                self.ebiz_invoice_status = 'delete'
                self.email_recieved_payments = False
                self.save_payment_link = False
                self.env.cr.commit()

                return message_wizard('Email pay request has been successfully canceled!')

        except Exception as e:
            raise ValidationError(e)

    def mark_as_applied(self):
        """
            Niaz Implementation:
            Once invoice paid via email, this function mark it as applied and remove from received list.
        """
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            recieved_payments = ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                'securityToken': ebiz._generate_security_json(),
                'paymentInternalId': self.payment_internal_id,

            })

            if recieved_payments.Status == 'Success':
                self.ebiz_invoice_status = 'applied'
                self.env.cr.commit()

        except Exception as e:
            raise ValidationError(e)

    def show_pending_ebiz_email(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        today = datetime.now()
        end = today + timedelta(days=1)
        start = today + timedelta(days=-365)

        recieved_payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**{
            'securityToken': ebiz._generate_security_json(),
            'fromPaymentRequestDateTime': str(start.date()),
            'toPaymentRequestDateTime': str(end.date()),
            'start': 0,
            'limit': 10000,
        })
        invoice_check = True

        if recieved_payments:
            import json
            import ast
            for invoice in recieved_payments:
                odoo_invoice = self.env['account.move'].search(
                    [('payment_internal_id', '=', invoice['PaymentInternalId']),
                     ('ebiz_invoice_status', '=', 'pending')])

                if odoo_invoice and odoo_invoice.id == self.id:
                    self.email_recieved_payments = True
                    text = f"There is an email payment of {float(invoice['PaidAmount'])} received on this {self.name}.\nDo you want to apply?"
                    wizard = self.env['wizard.recieve.email.pay'].create({"record_id": self.id,
                                                                               "odoo_invoice": odoo_invoice.id,
                                                                               "text": text})
                    action = self.env.ref('payment_ebizcharge.wizard_recieved_email_pay').read()[0]
                    action['res_id'] = wizard.id
                    action['context'] = dict(
                        invoice=invoice,
                    )
                    return action
                else:
                    continue


        today = datetime.now()
        end = today + timedelta(days = 1)
        start = today + timedelta(days = -7)
        params = {
            'securityToken': ebiz._generate_security_json(),
            # "customerId": self.partner_id.id,
            'fromPaymentRequestDateTime': str(start.date()),
            'toPaymentRequestDateTime': str(end.date()),
            "filters": {
                "SearchFilter": [{
                    'FieldName': 'InvoiceNumber',
                    'ComparisonOperator': 'eq',
                    'FieldValue': str(self.name)
                }]
            },
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.SearchEbizWebFormPendingPayments(**params)
        payment_lines = []

        if not payments:
            return message_wizard('Cannot find any pending payments')

        for payment in payments:
            payment_line = {
                "payment_type": payment['PaymentType'],
                "payment_internal_id": payment['PaymentInternalId'],
                "customer_id": payment['CustomerId'],
                "invoice_number": payment['InvoiceNumber'],
                "invoice_internal_id": payment['InvoiceInternalId'],
                "invoice_date": payment['InvoiceDate'],
                "invoice_due_date": payment['InvoiceDueDate'],
                "po_num": payment['PoNum'],
                # "so_num": payment[''],
                "currency_id": self.env.user.currency_id.id,
                "invoice_amount": payment['InvoiceAmount'],
                "amount_due": payment['AmountDue'],
                "email_amount": payment['AmountDue'],
                # "currency": payment[''],
                "auth_code": payment['AuthCode'],
                "ref_num": payment['RefNum'],
                "payment_method": payment['PaymentMethod'],
                "date_paid": datetime.strptime(payment['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                # "date_paid": payment['PaymentRequestDateTime'].split('T')[0] + ' ' + payment['PaymentRequestDateTime'].split('T')[1],
                "paid_amount": payment['PaidAmount'],
                "type_id": payment['TypeId'],
                "email_id": payment['CustomerEmailAddress'],
            }
            payment_lines.append([0,0, payment_line])
        wiz = self.env['ebiz.pending.payment'].create({})
        wiz.payment_lines = payment_lines
        action = self.env.ref('payment_ebizcharge.action_ebiz_pending_payments_form').read()[0]
        action['res_id'] = wiz.id
        return action 

    def _ebiz_check_invoice_update(self, values):
        """
        Kuldeeps implementation 
        def: checks if the after updating the Invoice should we run update sync base on the
        values that are updating.
        @params:
        values : update values params
        """
        update_fields = ["partner_id", "name", "invoice_date", "amount_total", "invoice_date_due",
         "amount_total", "currency_id", "amount_tax", "user_id", "invoice_line_ids", "amount_residual",
         "ebiz_invoice_status"]
        for update_field in update_fields:
            if update_field in values:
                return True
        return False

    def email_receipt_ebiz(self):
        """
            Niaz Implementation:
            Email the receipt to customer, if email receipts tempalates not ther in odoo, it will fetch.
            return: wizard to select the receipt template
        """

        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            reciepts = ebiz.client.service.GetReceiptsList(**{
                'securityToken': ebiz._generate_security_json(),
                'receiptType': 'Email',
            })

            if reciepts:
                for template in reciepts:
                    odoo_temp = self.env['email.receipt'].search([('receipt_id', '=', template['ReceiptRefNum'])])
                    if not odoo_temp:
                        self.env['email.receipt'].create({
                            'name': template['Name'],
                            'receipt_subject': template['Subject'],
                            'receipt_from_email': template['FromEmail'],
                            'receipt_id': template['ReceiptRefNum'],
                        })

            self.env.cr.commit()

            return {'type': 'ir.actions.act_window',
                    'name': _('Email Receipt'),
                    'res_model': 'wizard.email.receipts',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_contacts_to': [[6, 0, [self.partner_id.id]]],
                        'default_record_id': self.id,
                        'default_email_transection_id': self.receipt_ref_num,
                        'default_model_name': str(self._inherit),
                        'default_email_customer': str(self.partner_id.email),
                        'selection_check': 1,
                    },
                    }

        except Exception as e:
            raise ValidationError(e)

    def view_logs(self):
        return {
            'name': (_('Invoices Logs')),
            # 'domain': [('from_model', '=', 'Contacts'), ('contact_name', '=', self.id)],
            'view_type': 'form',
            'res_model': 'invoices.logs',
            'target': 'new',
            'view_id': False,
            'view_mode': 'tree,pivot,form',
            'type': 'ir.actions.act_window',
        }

    def request_email_invoice_bulk(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            templates = ebiz.client.service.GetEmailTemplates(**{
                'securityToken': ebiz._generate_security_json(),
            })

            if templates:
                for template in templates:
                    odoo_temp = self.env['email.templates'].search(
                        [('template_id', '=', template['TemplateInternalId'])])
                    if not odoo_temp:
                        self.env['email.templates'].create({
                            'name': template['TemplateName'],
                            'template_id': template['TemplateInternalId'],
                            'template_subject': template['TemplateSubject'],
                            'template_description': template['TemplateDescription'],
                            'template_type_id': template['TemplateTypeId'],
                        })
                    else:
                        odoo_temp.write({
                            'template_subject': template['TemplateSubject'],
                        })

            self.env.cr.commit()

            invoice_ids = [ids.id for ids in self if ids.payment_state != 'paid']
            if not invoice_ids:
                raise UserError('The Selected invoices are already Paid!')

            return {'type': 'ir.actions.act_window',
                    'name': _('Email Pay Request'),
                    'res_model': 'multiple.email.invoice.payments',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_invoicess_to': [[6, 0, invoice_ids]],
                        # 'default_record_id': self.id,
                        # 'default_currency_id': self.currency_id.id,
                        # 'default_amount': self.amount_residual if self.amount_residual else self.amount_total,
                        # 'default_model_name': str(self._inherit),
                        # 'default_email_customer': str(self.partner_id.email),
                        'selection_check': 1,
                    },
                    }

        except Exception as e:
            raise ValidationError(e)

    def button_draft(self):
        sync = False
        if not self.payment_state == 'paid' and not self.done_transaction_ids:
            sync = True
        ret = super(AccountMove, self).button_draft()

        if (self.move_type == "out_refund" or self.move_type == "out_invoice") and self.ebiz_internal_id and sync:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            ebiz.client.service.UpdateInvoice(**{
                'securityToken': ebiz._generate_security_json(),
                'invoice': {
                    "AmountDue": 0,
                    "InvoiceAmount": 0,
                    "NotifyCustomer": False,
                },
                'customerId': self.partner_id.id,
                'invoiceNumber': self.name,
                'invoiceInternalId': self.ebiz_internal_id
            })

        return ret

    # def button_draft(self):
    #
    #     if self.payment_state == 'paid':
    #         # if self.done_transaction_ids and self.done_transaction_ids.payment_id:
    #
    #         ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
    #
    #         payment_ref = self.env['account.payment'].search([('communication','=', self.name)])
    #         if payment_ref:
    #             for ref in payment_ref:
    #                 if ref.invoice_ids == self:
    #                     inv_params = {
    #                         'securityToken': ebiz._generate_security_json(),
    #                         'invoice': {
    #                             "CustomerId": self.partner_id.id,
    #                             # "SubCustomerId":"",
    #                             # "InvoiceNumber": self.name,
    #                             "InvoiceNumber": ref.name or '',
    #                             "InvoiceDate": str(self.invoice_date) if self.invoice_date else False,
    #                             "InvoiceAmount": -ref.amount,
    #                             "InvoiceDueDate": str(self.invoice_date_due) if self.invoice_date_due else False,
    #                             "AmountDue": -ref.amount,
    #                             "Software": "Odoo CRM",
    #                             "NotifyCustomer": False,
    #                             "Currency": self.currency_id.name,
    #                             # "EmailTemplateID": "",
    #                             # "URL": "",
    #                             "TotalTaxAmount": self.amount_tax_signed,
    #                             "InvoiceUniqueId": self.id,
    #                             # "Description": "Invoice",
    #                             # "CustomerMessage": "",
    #                             "InvoiceMemo": ref.communication or "",
    #                             # "InvoiceShipDate": str(invoice.expected_date.date()),
    #                             # "InvoiceShipVia": "",
    #                             "InvoiceSalesRepId": self.user_id.id,
    #                             "PoNum": self.ref or "",
    #                             # "InvoiceTermsId": "",
    #                             "InvoiceIsToBeEmailed": 0,
    #                             "InvoiceIsToBePrinted": 0,
    #                             # "Items": self._invoice_lines_params(self.invoice_line_ids),
    #
    #                             # 'ShippingAddress': self._get_customer_address(self.partner_shipping_id) if self.partner_shipping_id else '',
    #                         }
    #                     }
    #                     res = ebiz.client.service.AddInvoice(**inv_params)
    #
    #         ret = super(AccountMove, self).button_draft()
    #     else:
    #         ret = super(AccountMove, self).button_draft()

    def _invoice_lines_params(self, invoice_lines):
        lines_list = []
        for i,line in enumerate(invoice_lines):
            lines_list.append(self._invoice_line_params(line, i+1))
        array_of_items = self.client.get_type('ns0:ArrayOfItem')
        return array_of_items(lines_list)

    def _get_customer_address(self, partner):

        name_array = partner.name.split(' ') if partner.name else False
        first_name = name_array[0] if name_array else ''
        if name_array and len(name_array) >= 2:
            last_name = " ".join(name_array[1:])
        else:
            last_name = ""
        Address = {
            "FirstName": first_name,
            "LastName": last_name,
            "CompanyName": partner.name if partner.company_type == "company" else partner.parent_id.name or "",
            "Address1": partner.street or "",
            "Address2": partner.street2 or "",
            "City": partner.city or "",
            "State": partner.state_id.name or "",
            "ZipCode": partner.zip or "",
            "Country": partner.country_id.code or "US"
        }
        return Address

    def _invoice_line_params(self, line, item_no):
        item = {
            "ItemId": line.product_id.id,
            "Name": line.product_id.name,
            "Description": line.product_id.name,
            "UnitPrice": line.price_unit,
            "Qty": line.quantity,
            # "Taxable": True if line.product_id.taxes_id else False,
            "Taxable": False,
            "TaxRate": 0,
            "GrossPrice": 0,
            "WarrantyDiscount": 0,
            "SalesDiscount": 0,
            "UnitOfMeasure": line.product_id.uom_id.name,
            "TotalLineAmount": line.price_subtotal,
            # "TotalLineTax": line.tax_base_amount,
            "TotalLineTax": 0,
            "ItemLineNumber": item_no
        }
        return item

    def js_assign_outstanding_line(self, line_id):
        # return True
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)

        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        from_date = datetime.strftime((self.create_date - timedelta(days = 1)), '%Y-%m-%dT%H:%M:%S')
        to_date = datetime.strftime((datetime.now() + timedelta(days = 1)), '%Y-%m-%dT%H:%M:%S')
        params = {
            'securityToken': ebiz._generate_security_json(),
            "fromDateTime": from_date,
            "toDateTime": to_date,
            "customerId": self.partner_id.id,
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.GetPayments(**params)
        payments = list(filter(lambda x: x['InvoiceNumber'] == lines.payment_id.name, payments or []))
        if payments:
            for payment in payments:
                resp = ebiz.client.service.MarkPaymentAsApplied(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': payment['PaymentInternalId'],
                    'invoiceNumber': lines.payment_id.name
                    })

            payment_id = lines.payment_id
            payment_id.action_draft()
            payment_id.cancel()
            # context = dict(self._context)
            # context['message'] = f'This {payment_id.name} has already been processed on the ebiz portal! This {payment_id.name} will automactically be marked as paid.'
            # return self.message_wizard(context)

        else:
            return super(AccountMove, self).js_assign_outstanding_line(line_id)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AccountMove, self).fields_view_get(view_id, view_type, toolbar, submenu)
        if toolbar:
            actions = result['toolbar']['action']
            if self._context.get('ebiz_upload_invoice_action'):
                result['toolbar']['action'] = [action for action in actions if action['name'] == 'Upload']
            if self._context.get('ebiz_batch_process_action'):
                result['toolbar']['action'] = [action for action in actions if action['name'] == 'Process']
            if self._context.get('ebiz_email_pay_bulk_action'):
                result['toolbar']['action'] = [action for action in actions if action['name'] == 'Send Email']
        return result

    def generate_payment_link(self):
        """
        Niaz Implementation:
        Call the wizard, use to send email invoice to customer, fetch the email templates incase not present before
        return: Wizard
        """
        try:
            if self.move_type != 'out_invoice':
                raise UserError('Generating an EBizCharge payment link is only available for invoice payments.')

            if self.amount_residual <= 0:
                raise UserError('The value of the payment amount must be positive.')

            if self.state != 'posted':
                self.action_post()

            if not self.ebiz_internal_id:
                self.sync_to_ebiz()

            if self.save_payment_link:
                return {'type': 'ir.actions.act_window',
                        'name': _('Copy Payment Link'),
                        'res_model': 'ebiz.payment.link.copy',
                        'target': 'new',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'context': {
                            'default_link': self.save_payment_link,
                        },
                        }
            else:
                return {'type': 'ir.actions.act_window',
                        'name': _('Generate Payment Link'),
                        'res_model': 'ebiz.payment.link.wizard',
                        'target': 'new',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'context': {
                            'active_id': self.id,
                            'active_model': 'account.move',
                        },
                        }

        except Exception as e:
            raise ValidationError(e)


class AccountReceipts(models.Model):

    _name = 'account.move.receipts'

    invoice_id = fields.Char('Invoice ID')
    name = fields.Char('Name')
    ref_nums = fields.Char('Ref Num')
    model = fields.Char('Model Name')
