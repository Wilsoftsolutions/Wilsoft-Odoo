# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import EbizChargeAPI
from datetime import datetime, timedelta
import logging
import base64
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class TransactionHistory(models.TransientModel):

    _name = 'transaction.history'
    _order = 'date_time desc'

    def _default_get_start(self):
        return self.env['res.config.settings'].get_document_download_start_date()

    def _get_transaction_history_lines(self):
        end = self._default_get_end_date()
        start = self._default_get_start()
        filters = [
            self._get_filter_object('created','gt',str(start)),
            self._get_filter_object('created', 'lt', str(end))
        ]
        list_of_trans = self._get_transactions_data(filters)
        return list(map(lambda x: [0, 0, x], list_of_trans))

    def _get_filter_object(self, field_name, operator, value):
        return {'FieldName': field_name, 
            'ComparisonOperator': operator, 
            'FieldValue': value}

    def _default_get_end_date(self):
        today = datetime.now()+timedelta(days=1)
        return today.date()

    start_date = fields.Date(string='From Date', default=_default_get_start)
    end_date = fields.Date(string='To Date', default=_default_get_end_date)

    select_date = fields.Date(string='Select Date')
    add_filter = fields.Boolean(string='Filters')
    customer_id = fields.Char(string='Customer ID')
    invoice_id = fields.Char(string='Number')
    ref_no = fields.Char(string='Reference Number')
    account_holder = fields.Char(string='Name On Card/Account')
    date_time = fields.Datetime(string='Date & Time')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    amount = fields.Float(string='Amount')
    transaction_type = fields.Char(string='Transaction Type')
    transaction_status = fields.Char(string='Result')
    card_no = fields.Char(string='Payment Method')
    status = fields.Char(string='Status')
    email_id = fields.Char(string='Email')
    auth_code = fields.Char(string='Auth Code')
    source = fields.Char(string='Source')
    card_no_ecom = fields.Char(string='Payment Method')
    payment_method_icon = fields.Many2one('payment.icon')
    custnumber = fields.Char('Customer Number')
    image = fields.Binary("Image", related="payment_method_icon.image", max_width=50, max_height=25)

    @api.model
    def get_card_type_selection(self):
        icons = self.env['payment.icon'].search([]).read(['name'])
        sel = [(i['name'][0], i['name']) for i in icons]
        return sel

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        today = datetime.now()
        end = today + timedelta(days=1)
        up_dom = []
        start = None
        new_domain = []
        filters_list = []

        for d in domain:
            if d in ["|", "&"]:
                pass
            else:
                new_domain.append(d)
        domain = new_domain
        for i, do in enumerate(domain):
            if do in ["|", "&"]:
                pass
            elif do[0] == 'date_time':
                start = do[2]
                if do[1] == '=':
                    start, end = do[2], do[2]
                    # break
                if do[1] in ['>=', '>']:
                    start = do[2]
                    if len(domain) > i + 1 and domain[i + 1][0] == "date_time":
                        if domain[i + 1][1] in ['<=', '<']:
                            end = domain[i + 1][2]
                            up_dom = domain[0:i] + domain[i + 2:]
                            break
                        else:
                            end = str(end.date())
                    else:
                        end = str(end.date())
                if do[1] in ['<=', '<']:
                    end = do[2]

                up_dom = domain[0:i] + domain[i + 1:]
                break

            else:
                up_dom.append(d)
        if not domain or not start:
            return []

        filters_list.append(self._get_filter_object('created', 'gte', start))
        filters_list.append(self._get_filter_object('created', 'lte', end ))
        try:
            transaction = self._get_transactions_data(filters=filters_list)
            self.env['transaction.history'].search([]).unlink()
            self.env['transaction.history'].create(transaction)
        except ValidationError:
            pass
        
        res = super(TransactionHistory, self).search_read(up_dom, fields, offset, limit, order)
        return res



        # today = datetime.now().date()
        # end = False
        # up_dom = domain[::-1]
        # filters_list = []
        # comparison = ''
        # no_filter_check = []
        # o1 = o2 = False
        # total_data = []
        #
        # stack = []
        # for c in domain[::-1]:
        #     if type(c) == list and c[0] in ['date_filter', 'date_time'] and len(domain) != 1:
        #         stack.append(c)
        #     elif c == '&' or c == '|' and not stack:
        #         if stack:
        #             s1 = stack.pop()
        #         if stack:
        #             s2 = stack.pop()
        #
        #         if c == '&':
        #             if s1 and s2:
        #                 o1 = s1
        #                 o2 = s2
        #                 s1 = s2 = False
        #                 if o1[1] == '>=' and o2[1] == '<=':
        #                     filters_list.append(self._get_filter_object('created', 'gte', o1[2].split(' ')[0]))
        #                     filters_list.append(self._get_filter_object('created', 'lte', o2[2].split(' ')[0]))
        #
        #                     transaction = self._get_transactions_data(filters=filters_list)
        #                     total_data.extend(transaction)
        #                     filters_list.clear()
        #                     no_filter_check.append(1)
        #                     up_dom.remove(c)
        #                     up_dom.remove(o1)
        #                     up_dom.remove(o2)
        #                 else:
        #                     for i in [o1, o2]:
        #                         if i[0] in ['date_time']:
        #                             comparison = self.get_operator(i[1])
        #
        #                             filters_list.append(self._get_filter_object('created', comparison, i[2].split(' ')[0]))
        #                             comparison = ''
        #                             # self.env["transaction.history"].search([]).unlink()
        #                             transaction = self._get_transactions_data(filters=filters_list)
        #                             # self.create(transaction)
        #                             total_data.extend(transaction)
        #                             no_filter_check.append(1)
        #
        #                         elif i[0] in ['date_filter']:
        #                             end = self.env['res.config.settings'].get_start_date(*i[2].split('-'))
        #
        #                             filters_list.append(self._get_filter_object('created', 'lt', str(today)))
        #                             filters_list.append(self._get_filter_object('created', 'gt', str(end)))
        #                             transaction = self._get_transactions_data(filters=filters_list)
        #                             total_data.extend(transaction)
        #                             no_filter_check.append(1)
        #
        #             if s1 and not s2:
        #                 if s1[0] in ['date_time']:
        #                     comparison = self.get_operator(s1[1])
        #                     filters_list.append(self._get_filter_object('created', comparison, s1[2].split(' ')[0]))
        #                     comparison = ''
        #                     # self.env["transaction.history"].search([]).unlink()
        #                     transaction = self._get_transactions_data(filters=filters_list)
        #                     # self.create(transaction)
        #                     total_data.extend(transaction)
        #                     no_filter_check.append(1)
        #                     up_dom.remove(s1)
        #                     up_dom.remove(c)
        #
        #                 elif s1[0] in ['date_filter']:
        #                     end = self.env['res.config.settings'].get_start_date(*s1[2].split('-'))
        #
        #                     filters_list.append(self._get_filter_object('created', 'lt', str(today)))
        #                     filters_list.append(self._get_filter_object('created', 'gt', str(end)))
        #                     transaction = self._get_transactions_data(filters=filters_list)
        #                     total_data.extend(transaction)
        #                     no_filter_check.append(1)
        #                     up_dom.remove(s1)
        #                     up_dom.remove(c)
        #                     s1 = False
        #
        #     elif len(domain) == 1 and c[0] in ['date_time', 'date_filter']:
        #         if c[0] in ['date_time']:
        #             comparison = self.get_operator(c[1])
        #             filters_list.append(self._get_filter_object('created', comparison, c[2].split(' ')[0]))
        #             comparison = ''
        #             # self.env["transaction.history"].search([]).unlink()
        #             transaction = self._get_transactions_data(filters=filters_list)
        #             # self.create(transaction)
        #             total_data.extend(transaction)
        #             no_filter_check.append(1)
        #             up_dom.remove(c)
        #
        #         elif c[0] in ['date_filter']:
        #             end = self.env['res.config.settings'].get_start_date(*c[2].split('-'))
        #
        #             filters_list.append(self._get_filter_object('created', 'lt', str(today)))
        #             filters_list.append(self._get_filter_object('created', 'gt', str(end)))
        #             transaction = self._get_transactions_data(filters=filters_list)
        #             total_data.extend(transaction)
        #             no_filter_check.append(1)
        #             up_dom.remove(c)
        #
        # for x in range(up_dom.count('&')):
        #     if len(up_dom) - up_dom.count('&') == up_dom.count('&') + 1:
        #         break
        #     else:
        #         up_dom.remove('&')
        #
        # self.env["transaction.history"].search([]).unlink()
        # # import pandas as pd
        # # d_unique = pd.DataFrame(total_data).drop_duplicates().to_dict('records')
        # self.create(total_data)
        # total_data.clear()
        # if not no_filter_check:
        #     self.env["transaction.history"].search([]).unlink()
        #     up_dom += domain
        #
        # res = super(TransactionHistory, self).search_read(up_dom[::-1], fields, offset, limit, order)
        # return res

    @api.model
    def fields_get(self, fields=None):
        hide = ['start_date', 'end_date', 'add_filter', 'currency_id', 'create_date', 'create_uid', 'write_date',
                'write_uid', 'select_date']
        res = super(TransactionHistory, self).fields_get()
        for field in hide:
            res[field]['selectable'] = False
        return res

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     up_dom = domain[::-1]
    #     filters_list = []
    #     comparison = ''
    #     no_filter_check = []
    #     total_data = []
    #
    #     stack = []
    #     for c in domain[::-1]:
    #         if type(c) == list and c[0] in ['select_date']:
    #             stack.append(c)
    #         elif c == '&':
    #             s1 = s2 = False
    #             if stack:
    #                 s1 = stack.pop()
    #             if stack:
    #                 s2 = stack.pop()
    #
    #             if s1 and s2:
    #                 if s1[1] == '>=' and s2[1] == '<=':
    #                     filters_list.append(self._get_filter_object('created', 'gte', s1[2]))
    #                     filters_list.append(self._get_filter_object('created', 'lte', s2[2]))
    #
    #                     transaction = self._get_transactions_data(filters=filters_list)
    #                     total_data.extend(transaction)
    #                     filters_list.clear()
    #                     no_filter_check.append(1)
    #                     up_dom.remove(c)
    #                     up_dom.remove(s1)
    #                     up_dom.remove(s2)
    #                     break
    #
    #     for x in range(up_dom.count('&')):
    #         if len(up_dom) - up_dom.count('&') == up_dom.count('&') + 1:
    #             break
    #         else:
    #             up_dom.remove('&')
    #
    #     self.env["transaction.history"].search([]).unlink()
    #     # import pandas as pd
    #     # d_unique = pd.DataFrame(total_data).drop_duplicates().to_dict('records')
    #     self.create(total_data)
    #     total_data.clear()
    #     if not no_filter_check:
    #         self.env["transaction.history"].search([]).unlink()
    #         up_dom += domain
    #
    #     res = super(TransactionHistory, self).search_read(up_dom[::-1], fields, offset, limit, order)
    #     return res

    def search_transaction(self):
        try:

            if not self.start_date and not self.end_date and not self.select_customer and not self.add_filter:
                raise UserError('No Option Selected!')

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            filters_list = []
            if self.start_date and self.end_date:
                filters_list.append({'FieldName': 'created', 'ComparisonOperator': 'gt', 'FieldValue': str(self.start_date)})
                filters_list.append({'FieldName': 'created', 'ComparisonOperator': 'lt', 'FieldValue': str(self.end_date)})

            if self.select_customer:
                filters_list.append({'FieldName': 'CustomerId', 'ComparisonOperator': 'eq', 'FieldValue': str(self.select_customer.ebiz_customer_id)})

            if self.add_filter:
                if self.field_name and self.camparizon_operater and self.field_value:
                    filters_list.append({'FieldName': self.field_name, 'ComparisonOperator': self.camparizon_operater,
                                                             'FieldValue': str(self.field_value)})

                if self.field_name_2 and self.camparizon_operater_2 and self.field_value_2:
                    filters_list.append({'FieldName': self.field_name_2, 'ComparisonOperator': self.camparizon_operater_2,
                                                             'FieldValue': str(self.field_value_2)})
                    
                if self.field_name_3 and self.camparizon_operater_3 and self.field_value_3:
                    filters_list.append({'FieldName': self.field_name_3, 'ComparisonOperator': self.camparizon_operater_3,
                                                             'FieldValue': str(self.field_value_3)})

            list_of_trans = self._get_transactions_data(filters_list)
            list_of_trans = list(map(lambda x: dict(x, **{'sync_transaction_id':self.id}), list_of_trans))
            if list_of_trans:
                self.env["sync.history.transaction"].search([]).unlink()
                self.env['sync.history.transaction'].create(list_of_trans)
            else:
                self.env["sync.history.transaction"].search([]).unlink()

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(e)

    def _get_transactions_data(self, filters):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        params = {
                    'securityToken': ebiz._generate_security_json(),
                    'filters': {'SearchFilter': filters},
                    'matchAll': True,
                    'countOnly': False,
                    'start': 0,
                    'limit': 100000,
                    'sort': 'DateTime'
            }
        list_of_trans = []
        transaction_history = ebiz.client.service.SearchTransactions(**params)['Transactions']
        if transaction_history and transaction_history['TransactionObject']:
            for transaction in transaction_history['TransactionObject']:
                if transaction['Details']['Invoice'] not in ['Token', 'PM'] and transaction['Details']['Amount'] != 0.05 and transaction['Response']['Result'] != 'Error':
                    odooImage = ''
                    c_type = ''
                    payment_method = False

                    if transaction['CreditCardData']['CardType']:
                        card_types = self.get_card_type_selection()
                        card_types = {x[0]: x[1] for x in card_types}
                        c_type = card_types['D' if transaction['CreditCardData']['CardType'] == 'DS' else transaction['CreditCardData']['CardType']]
                        odooImage = self.env['payment.icon'].search([('name', '=', c_type)]).id

                    if transaction['CreditCardData']['CardNumber']:
                        payment_method = c_type + ' ending in ' + transaction['CreditCardData']['CardNumber'][12:] if transaction['CreditCardData']['CardNumber'] else ''
                    elif transaction['CheckData']:
                        payment_method = 'ACH ending in ' + transaction['CheckData']['Account'][-4:] if transaction['CheckData']['Account'] else ''

                    dict1 = {
                        # 'sync_date': datetime.now(),
                        # 'name': transaction['ShippingAddress']['Firstname'] if 'Firstname' in transaction['ShippingAddress'] else '',
                        'customer_id': transaction['CustomerID'],
                        'invoice_id': transaction['Details']['Invoice'],
                        # 'order_id': transaction['Details']['OrderID'],
                        'ref_no': transaction['Response']['RefNum'],
                        'account_holder': transaction['AccountHolder'],
                        'date_time': datetime.strptime(transaction['DateTime'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=8),
                        'amount': transaction['Response']['AuthAmount'],
                        # 'tax': transaction['Details']['Tax'],
                        "currency_id": self.env.user.currency_id.id,
                        'transaction_type': transaction['TransactionType'],
                        # 'card_no': c_type + ' ending in ' + transaction['CreditCardData']['CardNumber'][12:] if transaction['CreditCardData']['CardNumber'] else '',
                        'card_no': payment_method,
                        'card_no_ecom': 'ending in ' + transaction['CreditCardData']['CardNumber'][12:] if transaction['CreditCardData']['CardNumber'] else '',
                        'payment_method_icon': odooImage,
                        'status': transaction['Response']['Status'],
                        'transaction_status': transaction['Response']['Result'],
                        'auth_code': transaction['Response']['AuthCode'],
                        'source': transaction['Source'],
                        'email_id': transaction['BillingAddress']['Email'] if transaction['BillingAddress']['Email'] != None else '',
                        'custnumber': transaction['Response']['CustNum'] or '',
                        # 'sync_transaction_id': self.id,
                    }
                    list_of_trans.append(dict1)
        return list_of_trans

    def credit_or_void(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            # lines = self.transaction_history_line
            # filter_record = self.transaction_history_line.filtered(lambda x: x.check_box == True)
            filter_record = self
            if not filter_record:
                raise UserError('Please select a record first.')
            
            list_of_sucess = 'Ref Num           :   Status\n\n'
            resp_lines = []
            success = 0
            failed = 0

            for line in filter_record:
                resp_line = {}

                resp_line.update({
                    'customer_name': line['account_holder'],
                    'customer_id': line['customer_id'],
                    'ref_num': line['ref_no'],
                })
                # if line.check_box:
                if line.transaction_status != "Approved" or line.transaction_type == "Credit":
                    continue

                if line.status in ["Pending", "Settled"]:
                    if 'Check' in line.transaction_type:
                        if line.transaction_type == 'Check (Sale)' and line.status == 'Settled':
                            continue

                        if line.transaction_type == 'Check (Credit)':
                            continue

                        command = 'CheckCredit'
                        # command = 'Void'
                        # if line.status == 'Settled':
                        #     command = "CheckCredit"

                        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                        methods = ebiz.client.service.GetCustomerPaymentMethodProfiles(
                            **{'securityToken': ebiz._generate_security_json(),
                               'customerToken': line.custnumber})

                        get_transaction = ebiz.client.service.GetTransactionDetails(
                            **{'securityToken': ebiz._generate_security_json(),
                               'transactionRefNum': line.ref_no})

                        tran_method_id = get_transaction['CheckData']['Account'][-4:]
                        method_id = False
                        for method in methods:
                            if method['MethodType'] == 'check':
                                if method['Account'][-4:] == tran_method_id:
                                    method_id = method['MethodID']
                                    break
                        if method_id:
                            resp = self.run_transaction_without_invoice(line, command, method_id)
                    else:
                        command = 'CreditVoid'
                     
                        resp = ebiz.execute_transaction(line.ref_no, {'command': command})

                else:
                    continue
                    
                if resp['ResultCode'] == 'A':
                    list_of_sucess += f'{line.ref_no}     :   Success\n'
                    resp_line['status'] = 'Success'
                    success += 1
                else:
                    list_of_sucess += f'{line.ref_no}     :   Failed ({resp["Error"]})!\n'
                    resp_line['status'] = 'Failed'
                    failed += 1

                resp_lines.append([0, 0, resp_line])

            # if ('Success' not in list_of_sucess) and ('Failed' not in list_of_sucess):
                # list_of_sucess = "Please select valid transaction for credit or void."
            if success == 0 and failed == 0:
                raise UserError('Please select valid transaction for credit or void.')
            # self.search_transaction()

            wizard = self.env['wizard.transaction.history.message'].create({'name': 'Message', 'lines_ids': resp_lines,
                                                                            'success_count': success,
                                                                            'failed_count': failed, })
            # action = self.env.ref('payment_ebizcharge.wizard_transaction_message_action').read()[0]
            # action['context'] = self._context
            # action['res_id'] = wizard.id
            # return action

            return {'type': 'ir.actions.act_window',
                    'name': 'Credit/Void',
                    'res_model': 'wizard.transaction.history.message',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': wizard.id,
                    'context': self._context
                    }

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(e)

    def run_transaction_without_invoice(self, trans_id, command, method_id):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        params = {
            "securityToken":ebiz._generate_security_json(),
            "custNum": trans_id.custnumber,
            "paymentMethodID": method_id,
            "tran": {
                "isRecurring":False,
                "IgnoreDuplicate": False,
                "Software":'Odoo CRM',
                "MerchReceipt":True,
                "CustReceiptName":'',
                "CustReceiptEmail":'',
                "CustReceipt": False,
                "ClientIP":'',
                # "CardCode": payment_token.card_code,
                "Command": command,
                "Details": {
                    'OrderID': "",
                    'Invoice': trans_id.invoice_id ,
                    'PONum': "",
                    'Description': command,
                    'Amount': trans_id.amount,
                    'Tax': 0,
                    'Shipping': 0,
                    'Discount': 0,
                    'Subtotal': trans_id.amount,
                    'AllowPartialAuth': False,
                    'Tip': 0,
                    'NonTax': True,
                    'Duty': 0
                },
            },
        }

        return ebiz.client.service.runCustomerTransaction(**params)

    def email_receipt_ebiz(self):
        """
            Niaz Implementation:
            Email the receipt to customer, if email receipts tempalates not ther in odoo, it will fetch.
            return: wizard to select the receipt template
        """

        try:
            if not self:
                raise UserError('Please select a record first!')

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

            return {'type': 'ir.actions.act_window',
                    'name': _('Email Receipt'),
                    'res_model': 'wizard.email.receipts.bulk',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_model_name': str(self._inherit),
                        'selection_check': 1,
                        'transaction_ids': self.ids,
                    },
                    }

        except Exception as e:
            raise ValidationError(e)

    def from_js(self):
        self.env['transaction.history'].search([]).unlink()


class ListSyncHistory(models.TransientModel):
    _name = 'sync.history.transaction'
    _order = 'date_time asc'

    sync_date = fields.Datetime('Execution Date/Time', required=True, default=fields.Datetime.now)

    sync_transaction_id = fields.Many2one('transaction.history', string='Partner Reference', required=True,
                                    ondelete='cascade', index=True, copy=False)

    name = fields.Char(string='Name')
    customer_id = fields.Char(string='Customer ID')
    invoice_id = fields.Char(string='Number')
    order_id = fields.Char(string='Order Number')
    ref_no = fields.Char(string='Reference Number')
    ref_no_op = fields.Char(string='Reference Number')
    account_holder = fields.Char(string='Name On Card/Account')
    # date_time = fields.Char(string='Date Time')
    date_time = fields.Datetime(string='Date & Time')
    # amount = fields.Char(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    amount = fields.Float(string='Amount')
    tax = fields.Char(string='Tax')
    transaction_type = fields.Char(string='Transaction Type')
    transaction_type_op = fields.Char(string='Transaction Type')
    transaction_status = fields.Char(string='Result')
    transaction_status_op = fields.Char(string='Result')
    card_no = fields.Char(string='Payment Method')
    status = fields.Char(string='Status')
    status_op = fields.Char(string='Status')
    field_name = fields.Char(string='Field Name')
    check_box = fields.Boolean('Select')
    email_id = fields.Char(string='Email')
    auth_code = fields.Char(string='Auth Code')
    source = fields.Char(string='Source')
    image = fields.Binary("Image", help="This field holds the image used for this payment method")



