# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, timedelta
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class PaymentMethodUI(models.TransientModel):
    _name = 'payment.method.ui'

    def _get_ebiz_customers(self):
        self.env["list.ebiz.customers"].search([]).unlink()
        list_of_customers = self.env['res.partner'].search([('ebiz_customer_id', '!=', False)])
        list_of_dict = []
        for customer in list_of_customers:
            list_of_dict.append({
                'customer_name': customer.id,
                'customer_id': customer.ebiz_customer_id,
                'email_id': customer.email,
                'customer_phone': customer.phone,
                'customer_city': customer.city,
            })
        return list(map(lambda x: [0, 0, x], list_of_dict))

    name = fields.Char(string='Request Payments Via Email')
    select_customer = fields.Many2one('res.partner', sting='Select Customer',
                                      domain="[('ebiz_customer_id', '!=', False)]")
    transaction_history_line = fields.One2many('list.ebiz.customers', 'sync_transaction_id', string=" ", copy=True,)
    transaction_history_line_pending = fields.One2many('list.pending.payments.methods',
                                                       'sync_transaction_id_pending', string=" ", copy=True,)
    transaction_history_line_received = fields.One2many('list.received.payments.methods',
                                                        'sync_transaction_id_received', string=" ", copy=True)
    add_filter = fields.Boolean(string='Filters')
    customer_selection = fields.Selection([
        ('all_customers', 'All Customers'),
        ('no_save_card', 'Customers with no saved cards'),
        ('no_save_back_ach', 'Customers with no saved bank accounts'),
        ('no_payment_method', 'Customers with no saved payment methods'),
        ('card_expiring_soon', 'Customers with cards expiring soon'),
        ('expired_card', 'Customers with expired cards'),
    ], string='Display', help="Select which customer you'd like to display", default='all_customers')
    # customer_selection = fields.Selection([
    #     ('all_customers', 'All Customers'),
    #     ('no_save_card', 'Customers with no saved cards'),
    #     ('no_save_back_ach', 'Customers with no saved bank accounts'),
    #     ('no_payment_method', 'Customers with no saved payment methods'),], string='Display', help="Select which customer you'd like to display", default='all_customers')


    @api.model
    def _default_get_start(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def _default_get_end_date(self):
        today = datetime.now()+timedelta(days=1)
        return today.date()

    def _default_get_start_recieved(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def _default_get_end_date_recieved(self):
        today = datetime.now()+timedelta(days=1)
        return today.date()

    start_date = fields.Date(string='From Date', default=_default_get_start)
    end_date = fields.Date(string='To Date', default=_default_get_end_date)
    start_date_received = fields.Date(string='From Date', default=_default_get_start_recieved)
    end_date_received = fields.Date(string='To Date', default=_default_get_end_date_recieved)
    showHideDiv_send = fields.Boolean("Show")
    showHideDiv_pending = fields.Boolean("Show")
    showHideDiv_added = fields.Boolean("Show")

    @api.model
    def create(self, values):
        if 'transaction_history_line' in values:
            values['transaction_history_line'] = None
            values['transaction_history_line_pending'] = None
            values['transaction_history_line_received'] = None
        res = super(PaymentMethodUI, self).create(values)
        return res

    def send_request_payment(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')

            customer_ids = []
            self.env['email.recipients'].search([]).unlink()
            for customer in kwargs['values']:
                recipient = self.env['email.recipients'].create({
                    'partner_id': customer['customer_id'],
                    'email': customer['email_id']
                })
                customer_ids.append(recipient.id)
                odoo_customer = self.env['res.partner'].search([('id', '=', customer['customer_id'])])
                if odoo_customer:
                    if odoo_customer.customer_rank > 0 and not odoo_customer.ebiz_internal_id:
                        odoo_customer.sync_to_ebiz()

            return {
                'type': 'ir.actions.act_window',
                'name': _('Request Payment Method'),
                'res_model': 'wizard.ebiz.request.payment.method.bulk',
                'target': 'new',
                'view_mode': 'form',
                'views': [[False, 'form']],
                'context': {
                    'default_partner_id': [[6, 0, customer_ids]],
                    'selection_check': 1,
                },
            }

        except Exception as e:
            raise ValidationError(e)

    def resend_email(self, *args, **kwargs):
        try:
            resp_lines = []
            success = 0
            failed = 0
            total_count = len(kwargs['values'])

            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')
            else:
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                for record in kwargs['values']:
                    resp_line = {}
                    resp_line['customer_name'] = resp_line['customer_id'] = record['customer_id']
                    resp_line['email_address'] = record['email_id']

                    form_url = ebiz.client.service.ResendEbizWebFormEmail(**{
                        'securityToken': ebiz._generate_security_json(),
                        'paymentInternalId': record['payment_internal_id'],
                    })
                    counter = self.env['rpm.counter'].search([('request_id', '=', record['payment_internal_id'])])
                    if counter:
                        counter[0].counter += 1
                    resp_line['status'] = 'Success'
                    success += 1

                    pending_methods = self.env['payment.method.ui'].search([])
                    for method in pending_methods:
                        if 'id' in record:
                            if method.transaction_history_line_pending:
                                for pending in method.transaction_history_line_pending:
                                    if pending.id == record['id']:
                                        pending.update({
                                            'no_of_times_sent': counter[0].counter
                                        })
                    resp_lines.append([0, 0, resp_line])

            wizard = self.env['wizard.multi.payment.message'].create({'name': 'resend', 'lines_ids': resp_lines,
                                                                      'success_count': success, 'failed_count': failed,
                                                                      'total': total_count})

            # self.search_pending_payments()

            return {'type': 'ir.actions.act_window',
                    'name': _('Request Payment Methods'),
                    'res_model': 'wizard.multi.payment.message',
                    'target': 'new',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'context':
                        self._context,

                    }

        except Exception as e:
                raise ValidationError(e)

    def search_pending_payments(self):
        try:
            if not self.start_date and not self.end_date:
                raise UserError('No Option Selected!')

            self.env['list.pending.payments.methods'].search([]).unlink()
            if not self.start_date < self.end_date:
                return message_wizard('From Date should be lower than the To date!', 'Invalid Date')

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            params = {
                'securityToken': ebiz._generate_security_json(),
                # "customerId": self.partner_id.id,
                'fromPaymentRequestDateTime': str(self.start_date),
                'toPaymentRequestDateTime': str(self.end_date + timedelta(days=1)),
                "filters": {
                    "SearchFilter": [{
                        'FieldName': 'InvoiceNumber',
                        'ComparisonOperator': 'eq',
                        'FieldValue': 'PM',
                    }]
                },
                "limit": 1000,
                "start": 0,
            }
            payments = ebiz.client.service.SearchEbizWebFormPendingPayments(**params)
            payment_lines = []

            list_of_customers = [(5, 0, 0)]
            list_of_received = [(5, 0, 0)]

            customers = self.env['res.partner'].search([('ebiz_internal_id', '!=', False)])
            for customer in customers:
                line = (0, 0, {
                    'customer_name': customer.id,
                    'customer_id': customer.id,
                    'email_id': customer.email,
                    'customer_phone': customer.phone,
                    'customer_city': customer.city,
                    'sync_transaction_id': self.id,
                })
                list_of_customers.append(line)

            list_of_received.extend(self.fetchReceivedPayments(self.start_date_received, self.end_date_received))

            self.update({
                'transaction_history_line': list_of_customers,
                'transaction_history_line_received': list_of_received,
            })

            if not payments:
                return ''

            for payment in payments:
                is_customer = self.env['res.partner'].search([('id', '=', int(payment['CustomerId']))])
                if is_customer:
                    counter = self.env['rpm.counter'].search([('request_id', '=', payment['PaymentInternalId'])])
                    payment_line = {
                        "customer_name": int(payment['CustomerId']),
                        # "customer_id": int(payment['CustomerId']),
                        "customer_id": payment['CustomerId'],
                        "email_id": payment['CustomerEmailAddress'],
                        "date_time": datetime.strptime(payment['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                        "payment_internal_id": payment['PaymentInternalId'],
                        "sync_transaction_id_pending": self.id,
                        'no_of_times_sent': counter.counter if counter else 1,
                    }
                    payment_lines.append(payment_line)
            self.env['list.pending.payments.methods'].create(payment_lines)

        except Exception as e:
                raise ValidationError(e)

    def search_received_payments(self):
        try:
            if not self.start_date_received and not self.end_date_received:
                raise UserError('No Option Selected!')

            self.env['list.received.payments.methods'].search([]).unlink()

            if not self.start_date_received < self.end_date_received:
                return message_wizard('From Date should be lower than the To date!', 'Invalid Date')

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            params = {
                'securityToken': ebiz._generate_security_json(),
                # "customerId": self.partner_id.id,
                'fromPaymentRequestDateTime': str(self.start_date_received),
                'toPaymentRequestDateTime': str(self.end_date_received + timedelta(days=1)),
                "filters": {
                    "SearchFilter": [{
                        'FieldName': 'InvoiceNumber',
                        'ComparisonOperator': 'eq',
                        'FieldValue': 'PM',
                    }]
                },
                "limit": 1000,
                "start": 0,
            }
            payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**params)
            payment_lines = []

            list_of_customers = [(5, 0, 0)]
            list_of_pending = [(5, 0, 0)]
            customers = self.env['res.partner'].search([('ebiz_internal_id', '!=', False)])
            for customer in customers:
                line = (0, 0, {
                    'customer_name': customer.id,
                    'customer_id': customer.id,
                    'email_id': customer.email,
                    'customer_phone': customer.phone,
                    'customer_city': customer.city,
                    'sync_transaction_id': self.id,
                })
                list_of_customers.append(line)

            list_of_pending.extend(self.fetchPendingPayments(self.start_date, self.end_date))

            self.update({
                'transaction_history_line': list_of_customers,
                'transaction_history_line_pending': list_of_pending,
            })

            if not payments:
                return ''

            for payment in payments:
                try:
                    is_customer = self.env['res.partner'].search([('id', '=', int(payment['CustomerId']))])
                    counter = self.env['rpm.counter'].search([('request_id', '=', payment['PaymentInternalId'])])
                    if counter:
                        counter[0].unlink()
                    if is_customer:
                        payment_line = {
                            "customer_name": int(payment['CustomerId']),
                            "customer_id": int(payment['CustomerId']),
                            "email_id": payment['CustomerEmailAddress'],
                            "date_time": datetime.strptime(payment['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                            "payment_internal_id": payment['PaymentInternalId'],
                            "payment_method": payment['PaymentMethod'] + ' ending in ' + payment['Last4'],
                            "sync_transaction_id_received": self.id,
                            "customer_token": is_customer.ebizcharge_customer_token,
                        }
                        payment_lines.append(payment_line)

                except:
                    pass
            self.env['list.received.payments.methods'].create(payment_lines)

        except Exception as e:
            raise ValidationError(e)

    def delete_invoice(self, *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')
            else:
                text = f"Are you sure you want to remove {len(kwargs['values'])} request(s) from Pending Requests?"
                wizard = self.env['wizard.delete.payment.methods'].create({"record_id": self.id,
                                                                              "record_model": self._name,
                                                                              "text": text})
                action = self.env.ref('payment_ebizcharge.wizard_delete_rpm_action').read()[0]
                action['res_id'] = wizard.id

                action['context'] = dict(
                    self.env.context,
                    kwargs_values=kwargs['values'],
                    pending_recieved='Pending Requests'
                )

                return action

        except Exception as e:
            raise ValidationError(e)

    def search_customers(self):
        try:
            list_of_pending = [(5, 0, 0)]
            list_of_received = [(5, 0, 0)]

            list_of_pending.extend(self.fetchPendingPayments(self.start_date, self.end_date))
            list_of_received.extend(self.fetchReceivedPayments(self.start_date_received, self.end_date_received))

            self.update({
                'transaction_history_line_pending': list_of_pending,
                'transaction_history_line_received': list_of_received,
            })

            if self.customer_selection:
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                self.env["list.ebiz.customers"].search([]).unlink()
                list_of_customers = False
                if self.customer_selection == 'all_customers':
                    list_of_customers = self.env['res.partner'].search([('ebiz_internal_id', '!=', False)])
                elif self.customer_selection == 'no_save_card':
                    params = {
                        'securityToken': ebiz._generate_security_json(),
                        'countOnly': False,
                        'start': 0,
                        'limit': 100000,
                    }
                    no_saved_card_ach = ebiz.client.service.GetPaymentMethodProfileCounts(**params)[
                        'PaymentMethodProfileCountsList']['PaymentMethodProfileCounts']

                    list_of_customers = []

                    for method in no_saved_card_ach:
                        if method['CreditCardsCount'] == 0:
                            local_customer = self.env['res.partner'].search([('ebiz_internal_id', '!=', False),
                                                                        ('id', '=', int(method['CustomerInformation']['CustomerId'])),
                                                                        ])
                            if local_customer:
                                list_of_customers.append(local_customer)

                elif self.customer_selection == 'no_save_back_ach':
                    params = {
                        'securityToken': ebiz._generate_security_json(),
                        # "filters": {
                        #     "SearchFilter": [{
                        #         'FieldName': 'BankAccountsCount',
                        #         'ComparisonOperator': 'eq',
                        #         'FieldValue': 0
                        #     }]
                        # },
                        'countOnly': False,
                        'start': 0,
                        'limit': 100000,
                    }
                    no_saved_card_ach = ebiz.client.service.GetPaymentMethodProfileCounts(**params)[
                        'PaymentMethodProfileCountsList']['PaymentMethodProfileCounts']
                    list_of_customers = []
                    for method in no_saved_card_ach:
                        if method['BankAccountsCount'] == 0:
                            try:
                                local_customer = self.env['res.partner'].search([('ebiz_internal_id', '!=', False),
                                                                             ('id', '=', int(method['CustomerInformation'][
                                                                                                 'CustomerId'])),])
                            except Exception as e:
                                continue

                            if local_customer:
                                list_of_customers.append(local_customer)

                elif self.customer_selection == 'no_payment_method':
                    params = {
                        'securityToken': ebiz._generate_security_json(),
                        'countOnly': False,
                        'start': 0,
                        'limit': 100000,
                    }
                    no_saved_card_ach = ebiz.client.service.GetPaymentMethodProfileCounts(**params)[
                        'PaymentMethodProfileCountsList']['PaymentMethodProfileCounts']
                    list_of_customers = []

                    for method in no_saved_card_ach:
                        if method['BankAccountsCount'] == 0 and method['CreditCardsCount'] == 0:
                            local_customer = self.env['res.partner'].search([('ebiz_internal_id', '!=', False),
                                                                             ('id', '=', int(method['CustomerInformation'][
                                                                                                 'CustomerId'])),
                                                                             ])
                            if local_customer:
                                list_of_customers.append(local_customer)

                elif self.customer_selection == 'expired_card':
                    list_of_customers = []
                    filters_list = []
                    ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

                    filters_list.append(
                        {'FieldName': 'ExpiredCreditCardsCount', 'ComparisonOperator': 'gt',
                         'FieldValue': 0})

                    params = {
                        'securityToken': ebiz._generate_security_json(),
                        'filters': {"SearchFilter": filters_list},
                        'countOnly': False,
                        'start': 0,
                        'limit': 100000,
                        'sort': 'DateTime'
                    }
                    cards = ebiz.client.service.GetCardsExpirationList(**params)['CardExpirationCountsList']
                    if cards:
                        cards_lists = cards['CardExpirationCounts']

                        for card in cards_lists:
                            try:
                                local_customer = self.env['res.partner'].search(
                                    [('ebiz_internal_id', '!=', False),
                                     ('ebiz_internal_id', '=',
                                      card['CustomerInformation']['CustomerInternalId'])])
                            except Exception as e:
                                continue

                            if local_customer:
                                list_of_customers.append(local_customer[0])

                    # customers = self.env['res.partner'].search([('ebiz_internal_id', '!=', False)])
                    # currentMonth = datetime.now().month
                    # currentYear = datetime.now().year
                    # for customer in customers:
                    #     add = False
                    #     if customer.payment_token_ids:
                    #         for token in customer.payment_token_ids:
                    #             if token.token_type == 'credit':
                    #                 if token.card_exp_year < str(currentYear):
                    #                     add = True
                    #                 elif token.card_exp_year == str(currentYear):
                    #                     if token.card_exp_month < str(currentMonth):
                    #                         add = True
                    #     if add:
                    #         list_of_customers.append(customer)

                elif self.customer_selection == 'card_expiring_soon':
                    return {'type': 'ir.actions.act_window',
                            'name': _('Are you sure?'),
                            'res_model': 'wizard.cards.expiring.soon',
                            'target': 'new',
                            'view_mode': 'form',
                            'view_type': 'form',
                            }

                list_of_dict = []
                if list_of_customers:
                    self.env["list.ebiz.customers"].search([]).unlink()
                    for customer in list_of_customers:
                        list_of_dict.append({
                            'customer_name': customer.id,
                            'customer_id': customer.id,
                            'email_id': customer.email,
                            'customer_phone': customer.phone,
                            'customer_city': customer.city,
                            'sync_transaction_id': self.id,
                        })
                    self.env['list.ebiz.customers'].create(list_of_dict)

            else:
                raise UserError('No option selected!')

        except Exception as e:
            raise ValidationError(e)

    def create_default_records(self):
        self.env["list.ebiz.customers"].search([]).unlink()
        list_of_customers = self.env['res.partner'].search([('ebiz_customer_id', '!=', False)])
        list_of_dict = []
        for customer in list_of_customers:
            if customer.customer_rank > 0:
                list_of_dict.append({
                    'customer_name': customer.id,
                    'customer_id': customer.ebiz_customer_id,
                    'email_id': customer.email,
                    'customer_phone': customer.phone,
                    'customer_city': customer.city,
                    'sync_transaction_id': self.id,
                })
        self.env['list.ebiz.customers'].create(list_of_dict)

    def delete_invoice_2(self,  *args, **kwargs):
        try:
            if len(kwargs['values']) == 0:
                raise UserError('Please select a record first!')
            else:
                text = f"Are you sure you want to remove {len(kwargs['values'])} payment method(s) from Added Payment Methods?"
                wizard = self.env['wizard.delete.payment.methods'].create({"record_id": self.id,
                                                                              "record_model": self._name,
                                                                              "text": text})
                action = self.env.ref('payment_ebizcharge.wizard_delete_rpm_action').read()[0]
                action['res_id'] = wizard.id

                action['context'] = dict(
                    self.env.context,
                    kwargs_values = kwargs['values'],
                    pending_recieved='Added Payment Methods'
                )

                return action
            # else:
            #     ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            #     for record in kwargs['values']:
            #         form_url = ebiz.client.service.DeleteEbizWebFormPayment(**{
            #             'securityToken': ebiz._generate_security_json(),
            #             'paymentInternalId': record['payment_internal_id'],
            #         })

            # self.search_received_payments()

            # return {'type': 'ir.actions.act_window',
            #         'name': _('Success'),
            #         'res_model': 'message.wizard',
            #         'target': 'new',
            #         'view_mode': 'form',
            #         'views': [[False, 'form']],
            #         'context': {
            #             'message': 'The payment method request was successfully removed.',
            #         },
            #         }

        except Exception as e:
            raise ValidationError(e)

    @api.model
    def load_views(self, views, options=None):
        self.env["list.pending.payments.methods"].search([]).unlink()
        self.env["list.received.payments.methods"].search([]).unlink()
        return super(PaymentMethodUI, self).load_views(views, options=options)

    @api.model
    def default_get(self, fields):
        res = super(PaymentMethodUI, self).default_get(fields)
        installing_module = self.env.context.get('install_module')
        if res and not installing_module:
            list_of_customers = [(5, 0, 0)]
            list_of_pending = [(5, 0, 0)]
            list_of_received = [(5, 0, 0)]

            customers = self.env['res.partner'].search([('ebiz_internal_id', '!=', False)])
            for customer in customers:
                line = (0, 0, {
                    'customer_name': customer.id,
                    'customer_id': str(customer.id),
                    'email_id': customer.email,
                    'customer_phone': customer.phone,
                    'customer_city': customer.city,
                    'sync_transaction_id': self.id,
                })
                list_of_customers.append(line)

            list_of_pending.extend(self.fetchPendingPayments(res['start_date'], res['end_date']))
            list_of_received.extend(self.fetchReceivedPayments(res['start_date_received'], res['end_date_received']))

            res.update({
                'transaction_history_line': list_of_customers,
                'transaction_history_line_pending': list_of_pending,
                'transaction_history_line_received': list_of_received,
            })
        return res

    def fetchPendingPayments(self, start, end):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        params = {
            'securityToken': ebiz._generate_security_json(),
            'fromPaymentRequestDateTime': str(start),
            'toPaymentRequestDateTime': str(end + timedelta(days=1)),
            "filters": {
                "SearchFilter": [{
                    'FieldName': 'InvoiceNumber',
                    'ComparisonOperator': 'eq',
                    'FieldValue': 'PM',
                }]
            },
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.SearchEbizWebFormPendingPayments(**params)
        payment_lines = []

        if not payments:
            return ''

        for payment in payments:
            is_customer = self.env['res.partner'].search([('id', '=', int(payment['CustomerId']))])
            if is_customer:
                counter = self.env['rpm.counter'].search([('request_id', '=', payment['PaymentInternalId'])])
                line = (0, 0, {
                    "customer_name": int(payment['CustomerId']),
                    # "customer_id": int(payment['CustomerId']),
                    "customer_id": payment['CustomerId'],
                    "email_id": payment['CustomerEmailAddress'],
                    "date_time": datetime.strptime(payment['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                    "payment_internal_id": payment['PaymentInternalId'],
                    "sync_transaction_id_pending": self.id,
                    'no_of_times_sent': counter.counter if counter else 1,
                })
                payment_lines.append(line)

        return payment_lines

    def fetchReceivedPayments(self, start, end):
        self.env['list.received.payments.methods'].search([]).unlink()
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        params = {
            'securityToken': ebiz._generate_security_json(),
            'fromPaymentRequestDateTime': str(start),
            'toPaymentRequestDateTime': str(end + timedelta(days=1)),
            "filters": {
                "SearchFilter": [{
                    'FieldName': 'InvoiceNumber',
                    'ComparisonOperator': 'eq',
                    'FieldValue': 'PM',
                }]
            },
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**params)
        payment_lines = []

        if not payments:
            return ''

        for payment in payments:
            try:
                is_customer = self.env['res.partner'].search([('id', '=', int(payment['CustomerId']))])
                if is_customer:
                    line = (0, 0, {
                        "customer_name": int(payment['CustomerId']),
                        # "customer_id": int(payment['CustomerId']),
                        "customer_id": payment['CustomerId'],
                        "email_id": payment['CustomerEmailAddress'],
                        "date_time": datetime.strptime(payment['PaymentRequestDateTime'], '%Y-%m-%dT%H:%M:%S'),
                        "payment_internal_id": payment['PaymentInternalId'],
                        "payment_method": payment['PaymentMethod'] + ' ending in ' + payment['Last4'],
                        "sync_transaction_id_received": self.id,
                        "customer_token": is_customer.ebizcharge_customer_token,
                    })
                    payment_lines.append(line)
            except:
                pass

        return payment_lines


class ListCustomers(models.TransientModel):
    _name = 'list.ebiz.customers'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id = fields.Many2one('payment.method.ui', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer', domain="[('ebiz_customer_id', '!=', False)]")
    # customer_name = fields.Char(string='Customers')
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    email_id = fields.Char(string='Email')
    customer_phone = fields.Char('Phone')
    customer_city = fields.Char('City')
    status = fields.Char(string='Status')

    def viewPaymentMethods(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Methods',
            'view_mode': 'tree',
            'res_model': 'payment.token',
            'domain': [('partner_id', '=', self.customer_name.id)],
            'context': "{'create': False}"
        }


class ListPendingMethods(models.TransientModel):
    _name = 'list.pending.payments.methods'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)
    sync_transaction_id_pending = fields.Many2one('payment.method.ui', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)
    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer', domain="[('ebiz_customer_id', '!=', False)]")
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    email_id = fields.Char(string='Email')
    date_time = fields.Datetime(string='Org. Date & Time Sent')
    payment_internal_id = fields.Char(string='Payment Internal Id')
    no_of_times_sent = fields.Integer("# of Times Sent")


class ListReceivedMethods(models.TransientModel):
    _name = 'list.received.payments.methods'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)
    sync_transaction_id_received = fields.Many2one('payment.method.ui', string='Partner Reference', required=True,
                                          ondelete='cascade', index=True, copy=False)

    customer_name = fields.Many2one('res.partner', string='Customer', domain="[('ebiz_customer_id', '!=', False)]")
    # customer_id = fields.Integer(string='Customer ID', related='customer_name.id')
    customer_id = fields.Char(string='Customer ID')
    email_id = fields.Char(string='Email')
    date_time = fields.Datetime(string='Date & Time Added')
    payment_internal_id = fields.Char(string='Payment Internal Id')
    payment_method = fields.Char('Payment Method')
    customer_token = fields.Char('Customer Token')


