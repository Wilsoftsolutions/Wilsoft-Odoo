# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import EbizChargeAPI
import logging
from datetime import datetime, timedelta
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = ['sale.order', 'ebiz.charge.api',]
    _name = 'sale.order'

    def _get_default_ebiz_auto_sync(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        return config.get('ebiz_auto_sync_sale_order', False)

    def _compute_ebiz_auto_sync(self):
        self.ebiz_auto_sync = False
        
    def _compute_receipt_status(self):
        for order in self:
            config = self.env['account.move.receipts'].search(
                [('invoice_id', '=', order.id)])
            # , ('model', '=', self._inherit[0])
            order.receipt_status = True if config else False

    ebiz_internal_id = fields.Char('Ebiz Internal Id', copy=False)
    # ebiz_transaction_id = fields.Char('Ebiz Transaction Id')
    ebiz_auto_sync = fields.Boolean(compute="_compute_ebiz_auto_sync", default=_get_default_ebiz_auto_sync)
    ebiz_transaction_id = fields.Many2one('ebiz.charge.transaction', copy=False)
    # refund_picking_ids = fields.One2many('stock.picking', string='Refund picking ids', compute="_compute_refund_picking_ids")
    done_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_done_transaction_ids',
                                                    string='Authorized Transactions', copy=False, readonly=True)

    payment_internal_id = fields.Char(string='Ebiz Email Responce', copy=False)

    ebiz_transaction_ref = fields.Char('Ebiz Transaction Ref', compute="_compute_trans_ref")
    is_invoice_paid = fields.Boolean(compute="_compute_invoice_payment_status")
    sync_status = fields.Char(string="EBizCharge Upload Status", compute="_compute_sync_status")
    sync_response = fields.Char(string="Sync Status", copy=False)
    last_sync_date = fields.Datetime(string="Upload Date & Time", copy=False)
    
    receipt_status = fields.Boolean(compute="_compute_receipt_status", default=False)
    amount_due_custom = fields.Monetary(compute="_compute_amount_due", string='Amount Due')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    ebiz_app_trans_internal_id = fields.Char("Ebiz Application Transaction Id", 
        copy=False)
    ebiz_application_transaction_ids = fields.One2many('ebiz.application.transaction', 'sale_order_id')
    customer_id = fields.Char("Customer Id", compute="_compute_customer_id")

    def _compute_customer_id(self):
        for sal in self:
            sal.customer_id = sal.partner_id.id

    def _compute_amount_due(self):
        for entry in self:
            entry.amount_due_custom = entry.invoice_ids[0].amount_residual if entry.invoice_ids else 0.0

    def _compute_sync_status(self):
        for order in self:
            order.sync_status = "Synchronized" if order.ebiz_internal_id else "Pending"

    def _compute_invoice_payment_status(self):
        self.is_invoice_paid = self.invoice_ids and self.invoice_ids[0].payment_state == "paid"
    
    def _compute_trans_ref(self):
        self.ebiz_transaction_ref = self.transaction_ids[0].acquirer_reference if self.transaction_ids else ""

    @api.depends('transaction_ids')
    def _compute_done_transaction_ids(self):
        for trans in self:
            trans.done_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'done')

    @api.model
    def create(self, values):
        config = self.env['res.config.settings'].default_get([])
        # raise Exception('check')
        sale_order = super(SaleOrder, self).create(values)
        if config.get('ebiz_auto_sync_sale_order'):
            sale_order.sync_to_ebiz()
        return sale_order

    def sync_to_ebiz_ind(self):
        self.sync_to_ebiz()
        return message_wizard('Sales order uploaded successfully!')

    def sync_to_ebiz(self, time_sample=None):
        self.ensure_one()
        ebiz = self.get_ebiz_charge_obj(self.website_id.id)
        update_params = {}

        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()

        if self.ebiz_internal_id:
            resp = ebiz.update_sale_order(self)

            self.env['logs.of.orders'].create({
                'order_no': self.id,
                'currency_id': self.env.user.currency_id.id,
                'customer_name': self.partner_id.id,
                'customer_id': self.partner_id.id,
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,
                'amount_total': self.amount_total,
                'amount_due': self.amount_due_custom,
                'order_date': self.date_order,
            })

        else:
            resp = ebiz.sync_sale_order(self)
            if resp['ErrorCode'] == 2:
                resp_search = self.ebiz_search_sale_order()
            update_params.update({'ebiz_internal_id': resp['SalesOrderInternalId'] or resp_search['SalesOrderInternalId']})

            self.env['logs.of.orders'].create({
                'order_no': self.id,
                'customer_name': self.partner_id.id,
                'customer_id': self.partner_id.id,
                'currency_id': self.env.user.currency_id.id,
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,
                'amount_total': self.amount_total,
                'amount_due': self.amount_due_custom,
                'order_date': self.date_order,
            })

        # reference_to_upload_saleorder = self.env['list.of.orders'].search([('order_id', '=', self.id)])
        # reference_to_upload_saleorder.last_sync_date = datetime.now()
        # reference_to_upload_saleorder.sync_status = resp['Error'] or resp['Status']
        update_params.update({
            "last_sync_date": fields.Datetime.now(),
            "sync_response": 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error']})
        self.write(update_params)
        self.ebiz_application_transaction_ids.ebiz_add_application_transaction()
        return resp

    def ebiz_search_sale_order(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.SearchSalesOrders(**{
                'securityToken': ebiz._generate_security_json(),
                'customerId': self.partner_id.id,
                'salesOrderNumber': self.name,
                'start':0,
                'limit':0,
                'includeItems': False
            })
        if resp:
            return resp[0]
        return resp

    def run_ebiz_transaction(self, payment_token_id, command):
        self.ensure_one()
        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()
        if not self.partner_id.payment_token_ids:
            raise ValidationError("Please enter payment methode profile on the customer.")

        ebiz = self.get_ebiz_charge_obj(self.website_id.id)
        if self.env.user._is_public():
            resp = ebiz.run_transaction(self, payment_token_id, command)
        else:
            resp =  ebiz.run_customer_transaction(self, payment_token_id, command)
        # resp['sale_order_id'] = self.id
        # resp['invoice_id'] = self.invoice_ids
        # self.ebiz_transaction_id = self.env['ebiz.charge.transaction'].create_transaction_record(resp)
        if self.invoice_ids:
            # self.invoice_ids.ebiz_transaction_id = self.ebiz_transaction_id
            self.invoice_ids.transaction_ids = [(6, 0, self.transaction_ids.ids)]
        return resp

    def run_ebiz_refund_transaction(self):
        self.ensure_one()
        if not self.partner_id.payment_token_ids:
            raise ValidationError("Please enter payment methode profile on the customer to run transaction.")
        vals = {
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
            'payment_token_id': self.partner_id.payment_token_ids.id,
        }
        self._create_payment_transaction(vals)
        return True

    def process_payment(self):
        payment_obj = {
            "sale_order_id": self.id,
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

    def payment_action_capture(self):
        # self.invoice_id.action_invoice_register_payment()
        # acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        # journal_id = acquirer.journal_id
        # if self.invoice_ids:
        #     if self.invoice_ids[0].state != 'posted':
        #         self.invoice_ids.action_post()

            # payment = self.env['account.payment']\
            #     .with_context(active_ids=self.invoice_ids.ids, active_model='account.move', active_id=self.invoice_ids.id)\
            #     .create({'journal_id': journal_id.id, 'payment_method_id': journal_id.inbound_payment_method_ids.id})
        for trans in self.authorized_transaction_ids:
            if trans.payment_id:
                trans.payment_id.action_post()
            else:
                trans._post_process_after_done()

        return super(SaleOrder, self).payment_action_capture()

    # def sync_multi_sale_orders(self):
    #     for so in self:
    #         so.sync_to_ebiz()
    #     return {}

    def sync_multi_sale_orders(self):

        time = datetime.now()
        set = self.env['ir.config_parameter'].set_param('payment_ebizcharge.time_spam_test_sale_order', time)
        time_sample = get = self.env['ir.config_parameter'].get_param('payment_ebizcharge.time_spam_test_sale_order')

        resp_lines = []
        success = 0
        failed = 0
        total = len(self)
        for so in self:
            resp_line = {
                    'customer_name': so.partner_id.name,
                    'customer_id': so.partner_id.id,
                    'order_number': so.name
                }
            try:
                resp = so.sync_to_ebiz(time_sample)
                resp_line['record_message'] = resp['Error'] or resp['Status']
            except Exception as e:
                _logger.exception(e)
                resp_line['record_message'] = str(e)
            if resp_line['record_message'] == 'Success' or resp_line['record_message'] =='Record already exists':
                success += 1
            else:
                failed += 1
            resp_lines.append([0, 0, resp_line])
            

        wizard = self.env['wizard.multi.sync.message'].create({'name': 'sales orders', 'order_lines_ids': resp_lines,
            'success_count': success, 'failed_count': failed, 'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def sync_multi_customers_from_upload_saleorders(self, list):
        saleorders_records = self.env['sale.order'].browse(list).exists()
        resp_lines = []
        success = 0
        failed = 0
        total = len(saleorders_records)
        for so in saleorders_records:
            resp_line = {
                'customer_name': so.partner_id.name,
                'customer_id': so.partner_id.id,
                'order_number': so.name
            }
            try:
                resp = so.sync_to_ebiz()
                resp_line['record_message'] = resp['Error'] or resp['Status']
            except Exception as e:
                _logger.exception(e)
                resp_line['record_message'] = str(e)
            if resp_line['record_message'] == 'Success' or resp_line['record_message'] == 'Record already exists':
                success += 1
            else:
                failed += 1
            resp_lines.append([0, 0, resp_line])

        wizard = self.env['wizard.multi.sync.message'].create({'name': 'sales orders', 'order_lines_ids': resp_lines,
                                                               'success_count': success, 'failed_count': failed,
                                                               'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def write(self, values):
        ret = super(SaleOrder, self).write(values)
        if 'ebiz_internal_id' in values:
            return ret
        if self._ebzi_check_update_sync(values):
            for order in self:
                if order.ebiz_internal_id:
                    order.sync_to_ebiz()
        return ret

    def _ebzi_check_update_sync(self, values):
        """
        Kuldeeps implementation 
        def: checks if the after updating the sale should we run update sync base on the
        values that are updating.
        @params:
        values : update values params
        """
        update_fields = ["partner_id", "name", "date_order", "amount_total", 
        "date_order", "amount_total", "currency_id", "amount_tax", "expected_date", 
        "user_id", "order_line", "state"]
        for update_field in update_fields:
            if update_field in values:
                return True

        return False

    def invoice_to_journal(self, amount):
        try:
            invoice = self.invoice_ids[0]
            
            if invoice.state != 'posted':
                invoice.action_post()

            journal_id = False
            payment_acq = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
            if payment_acq and payment_acq.state == 'enabled':
                journal_id = payment_acq.journal_id

            # journal_id = self.env['account.journal'].search([('name', '=', 'Ebiz')])
            if journal_id:
                payment = self.env['account.payment'] \
                    .with_context(active_ids=invoice.ids, active_model='account.move', active_id=invoice.id) \
                    .create(
                    {'journal_id': journal_id.id,
                     'payment_method_id': journal_id.inbound_payment_method_ids.id,
                     'amount': amount,
                     'token_type': None})
                payment.with_context({'pass_validation': True}).action_post()
                res = super(SaleOrder, invoice).payment_action_capture()
                return res
            else:
                raise UserError('Ebiz Journal Not Found!')

        except Exception as e:
            return e

    # def add_application_transaction(self):
    #     if self.ebiz_internal_id and self.website_id and \
    #     self.transaction_ids.acquirer_reference and not self.ebiz_app_trans_internal_id:
    #         ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

    #         params = {
    #             'securityToken':ebiz._generate_security_json(),
    #             'applicationTransactionRequest':{
    #                 'CustomerInternalId': self.partner_id.ebiz_internal_id,
    #                 'TransactionId': self.transaction_ids[0].acquirer_reference,
    #                 'TransactionTypeId': 'Authorized' if self.transaction_ids[0].state == 'authorized' else 'Captured',
    #                 'LinkedToTypeId': 'SalesOrder',
    #                 'LinkedToExternalUniqueId': self.id, 
    #                 'LinkedToInternalId': self.ebiz_internal_id, 
    #                 'SoftwareId': "Odoo CRM",
    #                 'TransactionDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #                 'TransactionNotes': "Order No: {}".format(self.name) 
    #             }
    #         }
    #         resp = ebiz.client.service.AddApplicationTransaction(**params)
    #         if resp['StatusCode'] == 1:
    #             self.ebiz_app_trans_internal_id = resp['ApplicationTransactionInternalId']
    #         return resp
    #     else:
    #         _logger.info('can not add application transaciton on order No: {}'.format(self.name))


class EbizApplicationTransactions(models.Model):
    _name = "ebiz.application.transaction"

    ebiz_internal_id = fields.Char('Application Transaction Internal Id')
    partner_id = fields.Many2one('res.partner')
    sale_order_id = fields.Many2one('sale.order')
    transaction_id = fields.Many2one('payment.transaction')
    transaction_type = fields.Char('Transaction Command')
    is_applied = fields.Boolean('Is Applied', default=False)

    def ebiz_add_application_transaction(self):
        for trans in self:
            trans.ebiz_single_application_transaction()

    def mark_application_transaciton_as_applied(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        for trans in self:
            if not self.is_applied:
                resp = ebiz.client.service.MarkApplicationTransactionAsApplied(**{
                    'securityToken': ebiz._generate_security_json(),
                    'applicationTransactionInternalId': trans.ebiz_internal_id
                    })
                if resp['StatusCode'] == 1:
                    self.is_applied = True

    def ebiz_single_application_transaction(self):
        if self.sale_order_id.ebiz_internal_id and self.sale_order_id.website_id and \
        self.transaction_id.acquirer_reference and not self.ebiz_internal_id:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            params = {
                'securityToken':ebiz._generate_security_json(),
                'applicationTransactionRequest':{
                    'CustomerInternalId': self.partner_id.ebiz_internal_id,
                    'TransactionId': self.transaction_id.acquirer_reference,
                    'TransactionTypeId': self.transaction_type,
                    'LinkedToTypeId': 'SalesOrder',
                    'LinkedToExternalUniqueId': self.sale_order_id.id, 
                    'LinkedToInternalId': self.sale_order_id.ebiz_internal_id, 
                    'SoftwareId': "Odoo CRM",
                    'TransactionDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'TransactionNotes': "Order No: {}".format(self.sale_order_id.name) 
                }
            }
            resp = ebiz.client.service.AddApplicationTransaction(**params)
            if resp['StatusCode'] == 1:
                self.ebiz_internal_id = resp['ApplicationTransactionInternalId']
                self.mark_application_transaciton_as_applied()
            return resp
        else:
            _logger.info('cannot add application transaciton on order No: {}'.format(self.sale_order_id.name))


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"


    @api.model
    def _default_get_is_website_order(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            return bool(sale_order.website_id)

        return False

    is_website_order = fields.Boolean("Is Website Order", default=_default_get_is_website_order)
