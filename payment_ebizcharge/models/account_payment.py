# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
import logging
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from .ebiz_charge import message_wizard
import ast
_logger = logging.getLogger(__name__)


class AccountPayments(models.Model):
    _inherit = ["account.payment", "ebiz.charge.api"]
    _name = "account.payment"


    @api.model
    def year_selection(self):
        today = fields.Date.today()
        # year =  # replace 2000 with your a start year
        year = today.year
        max_year = today.year+30
        year_list = []
        while year != max_year: # replace 2030 with your end year
            year_list.append((str(year), str(year)))
            year += 1
        return year_list

    @api.model
    def month_selection(self):
        m_list = []
        for i in range(1, 13):
            m_list.append((str(i), str(i)))
        return m_list

    def _get_transaction_command(self):
        config = self.env['res.config.settings'].default_get([])
        ebiz_order_transaction_commands = config['ebiz_invoice_transaction_commands']
        sel = []
        pre_auth = ('AuthOnly', 'Pre Auth')
        dep = ('Sale', 'Deposit')
        return [dep]
        # if ebiz_order_transaction_commands == "pre-auth-and-deposit":
        #     return [pre_auth, dep]
        # if ebiz_order_transaction_commands == "deposit":
        #     return [dep]
        # else: return [pre_auth]

    def _get_default_required_sc(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        return config.get('enable_cvv', False)

    def _compute_required_sc(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        self.required_security_code = config.get('enable_cvv', False)

    card_id = fields.Many2one('payment.token', 'Saved Card')
    security_code = fields.Char('Security Code')
    required_security_code = fields.Boolean(compute="_compute_required_sc", default=_get_default_required_sc)
    ach_id = fields.Many2one('payment.token', 'Saved Bank Account')
    token_type = fields.Selection([('ach', 'ACH'), ('credit', 'Credit Card')], string='Payment Token Type')
    transaction_command = fields.Selection(_get_transaction_command, string='Transaction Command', default="Sale")

    card_account_holder_name = fields.Char('Name on Card *')
    card_card_number = fields.Char('Card Number *')
    # card_card_expiration = fields.Date('Expiration Date')
    card_exp_year = fields.Selection(year_selection, 'Expiration Year *')
    card_exp_month = fields.Selection(month_selection, 'Expiration Month *')
    card_avs_street = fields.Char("Billing Address *")
    card_avs_zip = fields.Char('Zip / Postal Code *')
    card_card_code = fields.Char('Security Code *')
    card_card_type = fields.Char('Card Type')
    ach_account_holder_name = fields.Char("Account Holder Name *")
    ach_account = fields.Char("Account Number *")
    ach_account_type = fields.Selection([('Checking','Checking'),('Savings', 'Savings')], string='Account Type *', default="Checking")
    ach_routing = fields.Char('Routing Number *')
    # ach_drivers_license = fields.Char('Drivers License')
    # ach_drivers_license_state = fields.Char('Drivers License State')
    journal_code = fields.Char('Journal Name', compute="_compute_journal_code")
    payment_internal_id = fields.Char("Payment Internal Id", compute = "_compute_payment_internal_id", store=True)
    sub_partner_id = fields.Many2one('res.partner', "Sub Partner Id")
    transaction_ref = fields.Char('Acquirer Ref', compute="_compute_trans_ref", store=False)
    ebiz_send_receipt = fields.Boolean('Email Receipt', default = True)
    ebiz_receipt_emails = fields.Char('Email list', help="Comma Seperated Email list( email1,email2)")

    ach_functionality_hide = fields.Boolean(compute="check_if_merchant_needs_avs_validation",
                                            string='ach functionality',)
    card_functionality_hide = fields.Boolean(string='ach functionality')
    card_save = fields.Boolean('Save Card', default=True, readonly=True)
    bank_account_save = fields.Boolean('Save Bank Account', default=True, readonly=True)

    full_amount = fields.Boolean('Full Amount Check')
    new_card = fields.Boolean('New Card Check')

    @api.depends('journal_id')
    def check_if_merchant_needs_avs_validation(self):
        """
        Gets Merchant transaction configuration
        """
        config = self.env['res.config.settings'].sudo().default_get([])
        self.ach_functionality_hide = config.get('merchant_data')
        self.card_functionality_hide = config.get('allow_credit_card_pay')

    @api.onchange('ebiz_send_receipt')
    def _compute_emails(self):
        if self.ebiz_send_receipt:
            self.ebiz_receipt_emails = self.sub_partner_id.email

    @api.constrains('card_avs_zip')
    def card_avs_zip_length_id(self):
        for rec in self:
            if rec.card_avs_zip:
                if len(rec.card_avs_zip) > 15:
                    raise ValidationError(_('Zip / Postal Code must be less than 15 Digits!'))
                elif '-' in rec.card_avs_zip:
                    for mystr in rec.card_avs_zip.split('-'):
                        if not mystr.isalnum():
                            raise ValidationError(_("Zip/Postal Code can only include numbers, letters, and '-'."))
                elif not rec.card_avs_zip.isalnum():
                    raise ValidationError(_("Zip/Postal Code can only include numbers, letters, and '-'."))

    @api.constrains('card_card_number')
    def card_card_number_length_id(self):
        for rec in self:
            if rec.token_type == 'credit':
                if rec.card_card_number and (len(rec.card_card_number) > 19 or len(rec.card_card_number) < 13):
                    raise ValidationError(_('Card number should be valid and should be 13-19 digits!'))

    @api.constrains('amount')
    def _constraint_min_amount(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError(_('Payment amount must be greater than 0'))

    @api.constrains('ach_account')
    def ach_acc_number_length_id(self):
        for rec in self:
            if rec.token_type == 'ach':
                if rec.ach_account:
                    if not rec.ach_account.isnumeric():
                        raise ValidationError(_('Account number must be numeric only!'))
                    elif rec.ach_account and not (len(rec.ach_account) >= 4 and len(rec.ach_account) <= 17):
                        raise ValidationError(_('Account number should be 4-17 digits!'))

    @api.constrains('ach_routing')
    def ach_routing_number_length_id(self):
        for rec in self:
            if rec.token_type == 'ach':
                if rec.ach_routing and len(rec.ach_routing) != 9:
                    raise ValidationError(_('Routing number must be 9 digits!'))

    @api.constrains('card_card_code')
    def card_card_code_length(self):
        for rec in self:
            if rec.token_type == 'credit':
                if rec.card_card_code and (len(rec.card_card_code) != 3 and len(rec.card_card_code) != 4):
                    raise ValidationError(_('Security code must be 3-4 digits.'))\


    @api.constrains('security_code')
    def card_card_code_length_security_code(self):
        for rec in self:
            if rec.token_type == 'credit':
                if rec.security_code and (len(rec.security_code) != 3 and len(rec.security_code) != 4):
                    raise ValidationError(_('Security code must be 3-4 digits.'))

    @api.constrains('card_exp_month', 'card_exp_year')
    def card_expiry_date(self):
        today = datetime.now()
        for rec in self:
            if rec.token_type == 'credit' and rec.card_exp_month and rec.card_exp_year:
                if int(rec.card_exp_year) > today.year:
                    return 
                elif int(rec.card_exp_year) == today.year:
                    if int(rec.card_exp_month) >= today.month:
                        return
                raise ValidationError(_('Card is expired!'))

    def _compute_trans_ref(self):
        self.transaction_ref = self.payment_transaction_id.acquirer_reference if self.payment_transaction_id else ""
    
    def action_post(self):
        if len(self) > 1:
            return super(AccountPayments, self).action_post()
        if 'payment_data' in self._context:
            self_data = self._context['payment_data']
            self.ebiz_send_receipt = self_data['ebiz_send_receipt']
            self.ebiz_receipt_emails = self_data['ebiz_receipt_emails']

        config = self.env['res.config.settings'].sudo().default_get([])
        payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
        success_message_keyword = "processed"
        self.full_amount = False
        self.new_card = False

        if self.env.context.get('batch_processing'):
            command = self.transaction_command

            payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
            transactions = payments_need_trans._create_payment_transaction()
            resp = transactions.s2s_do_transaction(**{'command': command})

            receipt = self.env['account.move.receipts'].create({
                'invoice_id': self.env['account.move'].search([('name', '=', self.ref)]).id,
                'name': self.env.user.currency_id.symbol + str(transactions.amount) + ' Paid On ' +
                        str(datetime.now().date()),
                'ref_nums': resp['RefNum'],
            })

            res = super(AccountPayments, self).action_post()
            transactions._set_transaction_done()
            transactions._log_payment_transaction_received()
            return True

        if self.env.context.get('do_not_run_transaction'):
            self.payment_token_id = None
            super(AccountPayments, self).action_post()
            # self.invoice_ids.multi_sync_ebiz()
            return True            

        if not self.payment_transaction_id and self.journal_code == 'EBIZC':

            if self.env.context.get('pass_validation'):
                # raise ValidationError(_('Please select any payment method [Credit Card/Back Account]!'))
                self.payment_token_id = None
                super(AccountPayments, self).action_post()
                return True

            elif self_data['token_type'] == 'credit':
                command = self.transaction_command
                # success_message_keyword = "authorized" if command == 'AuthOnly' else 'deposited'
                if not self_data['card_id']:
                    my_card_no = self_data['card_card_number']
                    self.new_card = True
                    resp = self.run_new_card_flow()
                    if self.env.context.get('get_customer_profile'):
                        self.partner_id.with_context({'donot_sync': True}).ebiz_get_payment_methods()
                        self.payment_token_id = self.env['payment.token'].search([('ebizcharge_profile', '=', self.env.context.get('get_customer_profile'))])
                    elif resp and type(resp)== bool:
                        token_id = self.create_credit_card_payment_methode().id
                        self.payment_token_id = token_id
                    else:
                        return resp
                else:
                    if config.get('use_full_amount_for_avs'):
                    # if False:
                        self.full_amount = True
                    else:
                        resp = self.validate_card_runcustomertransaction()
                        avs_result = self.get_avs_result(resp)
                        if all([x == 'Match' for x in avs_result]) and resp['ResultCode'] == 'A':
                            pass
                        else:
                            return self.show_payment_response(resp, bypass_newcard_avs=True, saved_avs_card=True,
                                                              ebizcharge_profile=self.payment_token_id.ebizcharge_profile)

            elif self_data['token_type'] == 'ach':
                command = "Check"
                if not self_data['ach_id']:
                    token_id = self.create_bank_account().id
                    self.payment_token_id = token_id
            else:
                raise ValidationError(_('Please select any payment method [Credit Card/Bank Account]!'))

            payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
            transactions = payments_need_trans._create_payment_transaction()
            if self_data['card_id']:
                self_data['card_id'].card_code = self_data['security_code']

            if config.get('merchant_card_verification') == 'full-amount' and self.token_type == 'credit' and not self.card_id:
            # if True:
                resp = transactions.with_context({'run_transaction': True}).s2s_do_transaction(**{'command': command, 'card': my_card_no })
            else:
                self.is_internal_transfer = True
                if 'payment_data' in self._context:
                    if 'to_reconcile' in self._context['payment_data']:
                        self.ebiz_reconcile_payment(source='payment_data')
                super_check = super(AccountPayments, self).action_post()
                return True
                resp = transactions.s2s_do_transaction(**{'command': command})

            receipt = self.env['account.move.receipts'].create({
                'invoice_id': self.env['account.move'].search([('name', '=', self.ref)]).id,
                'name': self.env.user.currency_id.symbol + str(transactions.amount) + ' Paid On ' +
                        str(datetime.now().date()),
                'ref_nums': resp['RefNum'],
            })

            avs_result = self.get_avs_result(resp)
            # If merchant has full amount avs validation setting on 
            # then following code will run avs or proceed with the transactoin as usual
            if resp['ResultCode'] == 'A':
                # on successful invoice add payment on the invoice
                # if self.invoice_ids:
                #     pay_resp = self.invoice_ids.ebiz_add_invoice_payment()
                procceed = False
                # full_amount will only be set true if the transaction is with new card
                # so it will check for avs
                if self.full_amount:
                    if all([x == 'Match' for x in avs_result]):
                        procceed = True
                else:
                    procceed = True

                if procceed:
                    if command in ['Check', 'Sale']:
                        res = super(AccountPayments, self).action_post()
                        transactions._set_transaction_done()
                        transactions._log_payment_transaction_received()
                        # self.invoice_ids.multi_sync_ebiz()
                    # self.action_send_email_receipt()
                    return message_wizard('Transaction has been successfully {}!'.format(success_message_keyword))
                else:

                    if config.get('merchant_card_verification') == 'full-amount':
                    # if True:
                        return self.show_payment_response(resp, customer_token=self.payment_token_id.partner_id.ebizcharge_customer_token,
                                                          payment_method_id = self.payment_token_id.ebizcharge_profile)

                    elif self.card_id and not self.new_card:
                        return self.show_payment_response(resp, bypass_newcard_avs=True)
                    else:
                        return self.show_payment_response(resp)
            else:
                return self.show_payment_response(resp)

        elif not self.payment_transaction_id and self.journal_code == 'EBIZC:credit_note':
            payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
            transactions = payments_need_trans._create_payment_transaction()
            resp = transactions.s2s_do_transaction()
            avs_result = self.get_avs_result(resp)
            if resp['ResultCode'] == 'A':
                res = super(AccountPayments, self ).action_post()
                return True
            else:
                return self.show_payment_response(resp)
        else:
            res = super(AccountPayments, self).action_post()
            # self.invoice_ids.multi_sync_ebiz()

        if 'payment_data' in self._context:
            if 'to_reconcile' in self._context['payment_data']:
                self.ebiz_reconcile_payment(source='payment_data')
        return True

    def ebiz_reconcile_payment(self, source=False):
        if source:
            to_process = self.env['account.move.line'].search([('id', '=', self._context['payment_data']['to_reconcile'])])
        else:
            to_process = self.line_ids.filtered_domain([('debit', '>', 0)])
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_internal_type', 'in', ('receivable', 'payable')),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment_lines = self.line_ids.filtered_domain(domain)
            lines = to_process

            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                    .reconcile()

    def action_send_email_receipt(self):
        if self.send_email_receipt:
            if self.payment_transaction_id and self.payment_transaction_id.state in ['authorized', 'done']:
                emails = self.ebiz_receipt_emails.split(',')
                for email in emails:
                    self.email_receipt(email.strip())

    def email_receipt(self, email):
        ebiz = self.get_ebiz_charge_obj()
        params = {
                            'securityToken': ebiz._generate_security_json(),
                            'transactionRefNum': self.payment_transaction_id.acquirer_reference,
                            'receiptRefNum': self.ebiz_receipt_template.receipt_id,
                            'receiptName': self.ebiz_receipt_template.name,
                            'emailAddress': email,
                            # 'emailAddress': 'niazbscs1@gmail.com',
                        }
        form_url = ebiz.client.service.EmailReceipt(**params)

    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayments, self).default_get(default_fields)
        if 'partner_id' in rec:
            if rec['invoice_ids'][0][2]:
                invoice_ids = rec['invoice_ids'][0][2]
                if len(invoice_ids) > 1:
                    return rec
                sub_partner_id = self.env['account.move'].browse(invoice_ids).partner_id.id
                
            partner = self.env['res.partner'].browse(rec['partner_id'])
            rec.update({
                'sub_partner_id': sub_partner_id,
                'card_account_holder_name': partner.name,
                'card_avs_street': partner.street,
                'card_avs_zip': partner.zip,
                'ach_account_holder_name': partner.name,
            })
            partner.with_context({'donot_sync': True}).ebiz_get_payment_methods()
            # .ebiz_get_payment_methods()
        return rec

    @api.onchange('card_card_number', 'card_exp_month', 'card_exp_year', 'card_card_code')
    def _reset_card_id(self):
        if self.card_card_number or self.card_exp_year or self.card_exp_month or self.card_card_code:
            self.token_type = 'credit'
            self.card_id = None
            self.security_code = None

            self.ach_id = None
            self.ach_account = None
            self.ach_routing = None

    @api.onchange('ach_account', 'ach_routing')
    def _reset_ach_account(self):
        if self.ach_account or self.ach_routing:
            self.token_type = 'ach'
            self.ach_id = None

            self.security_code = None
            self.card_id = None
            self.card_card_number = None
            self.card_exp_year = None
            self.card_exp_month = None
            self.card_card_code = None

    @api.onchange('card_id')
    def _reset_new_card_fields(self):
        for payment in self:
            if payment.card_id:
                payment.token_type = 'credit'
                payment.payment_token_id = payment.card_id
                payment.card_card_number = None
                payment.card_exp_year = None
                payment.card_exp_month = None
                payment.card_card_code = None

                payment.ach_id = None
                payment.ach_account = None
                payment.ach_routing = None

    @api.onchange('ach_id')
    def _reset_new_ach_fields(self):
        for payment in self:
            if payment.ach_id:
                payment.token_type = "ach"
                payment.payment_token_id = payment.ach_id
                payment.ach_account = None
                payment.ach_routing = None

                payment.security_code = None
                payment.card_id = None
                payment.card_card_number = None
                payment.card_exp_year = None
                payment.card_exp_month = None
                payment.card_card_code = None

    def transaction_details(self):
        return {
            'OrderID': "Token",
            'Invoice': "Token",
            'PONum': "Token",
            'Description': 'description',
            'Amount': 0.05,
            'Tax': 0,
            'Shipping': 0,
            'Discount': 0,
            'Subtotal': 0.05,
            'AllowPartialAuth': False,
            'Tip': 0,
            'NonTax': True,
            'Duty': 0
        }

    def run_new_card_flow(self):
        self.ensure_one()
        if self.env.context.get('avs_bypass'):
            return True
        config = self.env['res.config.settings'].sudo().default_get([])
        avs_action = config.get('merchant_card_verification')
        # avs_action = 'no-validation'
        # avs_action = self.get_merchant_avs_validation_action()
        if avs_action == 'minimum-amount':
            resp = self.credit_card_validate_transaction()
            avs_result = self.get_avs_result(resp)
            if all([x == 'Match' for x in avs_result]) and resp['ResultCode'] == 'A':
                return True

        elif avs_action == "full-amount":
            self.full_amount = True
            return True
        elif avs_action == 'no-validation':
            if config.get('use_full_amount_for_avs'):
            # if False:
                self.full_amount = True
                return True
            else:
                resp = self.credit_card_validate_transaction()
                avs_result = self.get_avs_result(resp)
                if all([x == 'Match' for x in avs_result]) and resp['ResultCode'] == 'A':
                    return True
                else:
                    return self.show_payment_response(resp, my_full_amount=True)

        return self.show_payment_response(resp)

    def validate_card_runcustomertransaction(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            params = {
                "securityToken": ebiz._generate_security_json(),
                "custNum": self.partner_id.ebizcharge_customer_token,
                "paymentMethodID": self.payment_token_id.ebizcharge_profile,
                "tran": {
                    "isRecurring": False,
                    "IgnoreDuplicate": False,
                    "Details": self.transaction_details(),
                    "Software": 'Odoo CRM',
                    "MerchReceipt": True,
                    "CustReceiptName": '',
                    "CustReceiptEmail": '',
                    "CustReceipt": False,
                    "CardCode": self.payment_token_id.card_code,
                    "Command": 'AuthOnly',
                },
            }

            resp = ebiz.client.service.runCustomerTransaction(**params)
            resp_void = ebiz.execute_transaction(resp['RefNum'], {'command': 'Void'})
        except  Exception as e:
            _logger.exception(e)
            raise ValidationError(e)
        return resp

    def get_merchant_avs_validation_action(self):
        """
        Kuldeep implementation
        Gets Merchant transaction configuration
        """
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.GetMerchantTransactionData(**{
                'securityToken':ebiz._generate_security_json()
            })

        if resp['VerifyCreditCardBeforeSaving']:
            if resp['EnableAVSWarnings'] or resp['EnableCVVWarnings']:
                if resp['UseFullAmountForAVS']:
                    return 'full-amount'
                # return 'full-amount'
                return 'minimum-amount'
        else:
            return 'no-validation'

    def show_payment_response(self, resp, my_full_amount=None, customer_token=None, payment_method_id=None,
                              bypass_newcard_avs=None, saved_avs_card=None, ebizcharge_profile=None):
        action = self.env.ref('payment_ebizcharge.action_ebiz_transaction_validtion_form').read()[0]
        if resp['ResultCode'] == 'E':
            raise ValidationError(resp['Error'])
        card_code, address, zip_code = self.get_avs_result(resp)

        transaction_id = self.payment_transaction_id

        validation_params = {'address': address,
            'zip_code': zip_code,
            'card_code': card_code,
            # 'wizard_prcoess_id': self.id,
            'full_amount_avs': self.full_amount,
            'payment_id': self.id,
            'transaction_id': transaction_id.id,
            'check_avs_match': all([x == "Match" for x in [card_code, address, zip_code]])}
        if not self.new_card and not bypass_newcard_avs and all([x == "Match" for x in [card_code, address, zip_code]]):
            validation_params['check_avs_match'] = True

        if resp['ResultCode'] == 'D':
            validation_params['is_card_denied'] = True
            validation_params['denied_message'] = 'Card Declined' if 'Card Declined' in resp['Error'] else resp['Error']
            action['name'] = 'Card Declined'
        wiz = self.env['wizard.ebiz.transaction.validation'].create(validation_params)
        action['res_id'] = wiz.id
        action['context'] = {'payment_data': self._context['payment_data']}
        if my_full_amount:
            action['context'] = dict(
                my_full_amount=True,
            )

        if customer_token and payment_method_id:
            action['context'] = dict(
                customer_token_to_dell=customer_token,
                payment_method_id_to_dell=payment_method_id,
            )

        if saved_avs_card:
            action['context'] = dict(
                ebiz_charge_profile=ebizcharge_profile,
            )
        return action

    @api.onchange('journal_id')
    def _compute_journal_code(self):
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        for payment in self:
            if payment.journal_id.id == journal_id.id and ('payment_data' in self._context or payment.payment_type == 'outbound'):
                if 'active_id' in self._context and 'active_model' in self._context:
                    if self.env[self._context['active_model']].search([('id', '=', self._context['active_id'])]).move_type == 'out_refund':
                        payment.journal_code = 'EBIZC:credit_note'
                # if payment.move_id[0].move_type == "out_refund":
                #     payment.journal_code = 'EBIZC:credit_note'
                elif 'payment_data' in self._context:
                    payment.journal_code = "EBIZC"
                else:
                    payment.journal_code = "other"
            else:
                payment.journal_code = "other"

    @api.onchange('partner_id', 'payment_method_id', 'journal_id')
    def _onchange_set_payment_token_id(self):
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        journal_id = acquirer.journal_id
        su = super(AccountPayments,self)._onchange_set_payment_token_id()

        if self.invoice_line_ids and self.invoice_line_ids[0].type == "out_refund" and self.journal_id == journal_id:
            trans_ids = self.invoice_line_ids.reversed_entry_id.transaction_ids
            if trans_ids:
                self.payment_token_id = trans_ids[0].payment_token_id

        return su

    def create_credit_card_payment_methode(self):
        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()
        self_data = self._context['payment_data']
        params = {
            "account_holder_name": self_data['card_account_holder_name'],
            "name": self_data['card_account_holder_name'],
            "card_number": self_data['card_card_number'],
            "card_exp_year": self_data['card_exp_year'],
            "card_exp_month": self_data['card_exp_month'],
            "avs_street": self_data['card_avs_street'],
            "avs_zip": self_data['card_avs_zip'],
            "card_code": self_data['card_card_code'],
            # "card_type": self.card_card_type,
            # "partner_id": self.partner_id.id,
            "partner_id": self_data['sub_partner_id'],
            "acquirer_ref": "Temp",
            "verified": True,
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id
        }
        self.reset_crdit_card_fields()
        return self.env['payment.token'].create(params)

    def credit_card_validate_transaction(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            params = {
                "securityToken": ebiz._generate_security_json(),
                "tran": {
                    "IgnoreDuplicate": False,
                    "IsRecurring": False,
                    "Software":'Odoo CRM',
                    # "MerchReceipt":True,
                    # "CustReceiptName":'',
                    # "CustReceiptEmail":'',
                    "CustReceipt": False,
                    # "ClientIP":'117.102.0.94',
                    # "CardCode": self.card_card_code,
                    "Command": 'AuthOnly',
                    "Details": self.transaction_details(),
                    "CustomerID": self.partner_id.id,
                    "CreditCardData": self._get_credit_card_dict(),
                    "AccountHolder": self.card_account_holder_name,
                }
            }

            resp = ebiz.client.service.runTransaction(**params)
            resp_void = ebiz.execute_transaction(resp['RefNum'], {'command': 'Void'})
        except  Exception as e:
            _logger.exception(e)
            raise ValidationError(e)
        return resp

    def _get_credit_card_dict(self):
        return {
                'InternalCardAuth': False,
                'CardPresent': True,
                'CardNumber': self.card_card_number,
                # 'CardExpiration': self.card_card_expiration.strftime('%m%y'),
                "CardExpiration": "%s%s"%(self.card_exp_month, self.card_exp_year[2:] if self.card_exp_year else False),
                'CardCode': self.card_card_code,
                'AvsStreet': self.card_avs_street,
                'AvsZip': self.card_avs_zip
            }

    def transaction_details(self):
        return {
            'OrderID': "Token",
            'Invoice': "Token",
            'PONum': "Token",
            'Description': 'description',
            'Amount': 0.05,
            'Tax': 0,
            'Shipping': 0,
            'Discount': 0,
            'Subtotal': 0.05,
            'AllowPartialAuth': False,
            'Tip': 0,
            'NonTax': True,
            'Duty': 0
        }

    def create_bank_account(self):
        if not self.partner_id.ebiz_internal_id:
            self.partner_id.sync_to_ebiz()

        self_data = self._context['payment_data']

        params = {
            "account_holder_name": self_data['ach_account_holder_name'],
            "account_number": self_data['account_number'],
            "account_type": self_data['account_type'],
            "routing": self_data['routing'],
            # "partner_id": self.partner_id.id,
            "partner_id": self_data['sub_partner_id'],
            # "drivers_license": self.ach_drivers_license,
            # "drivers_license_state": self.ach_drivers_license_state,
            "token_type": 'ach',
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id   
        }

        return self.env['payment.token'].create(params)

    def get_avs_result(self, resp):
        # card_code =  resp['CardCodeResult']
        card_code = ''

        if resp['CardCodeResultCode'] == 'M':
            card_code = 'Match'
        elif resp['CardCodeResultCode'] == 'N':
            card_code = 'No Match'
        elif resp['CardCodeResultCode'] == 'P':
            card_code = 'Not Processed'
        elif resp['CardCodeResultCode'] == 'S':
            card_code = 'Should be on card but not so indicated'
        elif resp['CardCodeResultCode'] == 'U':
            card_code = 'Issuer Not Certified'
        elif resp['CardCodeResultCode'] == 'X':
            card_code = 'No response from association'
        elif resp['CardCodeResultCode'] == '':
            card_code = 'No CVV2/CVC data available for transaction'

        avs = resp['AvsResultCode']
        address, zip_code = 'No Match', 'No Match'

        if avs in ['YYY', 'Y', 'YYA', 'YYD']:
            address = zip_code = 'Match'
        if avs in ['NYZ', 'Z']:
            zip_code = 'Match'
        if avs in ['YNA', 'A', 'YNY']:
            address = 'Match'
        if avs in ['YYX', 'X']:
            address = zip_code = 'Match'
        if avs in ['NYW', 'W']:
            zip_code = 'Match'
        if avs in ['GGG', 'D']:
            address = zip_code = 'Match'
        if avs in ['YGG', 'P']:
            zip_code = 'Match'
        if avs in ['YYG', 'B', 'M']:
            address = 'Match'

        return card_code.strip(), address.strip(), zip_code.strip()

        # card_code = resp['CardCodeResult']
        # avs = resp['AvsResultCode']
        # address , zip_code= 'No Match', 'No Match'
        # if avs in ['YYY', 'YNA', 'YYX','YYG','GGG']:
        #     address = 'Match'
        # if avs in ['YYY', 'NYZ', 'YYX','NYW','GGG', 'YGG']:
        #     zip_code = 'Match'
        # return card_code.strip(), address.strip(), zip_code.strip()

    def reset_crdit_card_fields(self):
        self.write({
                "card_card_number": None,
                "card_exp_year": None,
                "card_exp_month": None,
                "card_avs_street":None,
                "card_avs_zip": None,
                "card_card_code": None,
                "card_card_type": None
            })

    def reset_ach_fields(self):
        self.write({
            "ach_account": None,
            "ach_routing": None
        })

    @api.depends('state')
    def _compute_payment_internal_id(self):
        for payment in self:
            if not payment.payment_internal_id:
                payment.ebiz_add_invoice_payment()
            # if there is any transaction mark that paid
            if self.payment_transaction_id:
                self.payment_transaction_id.write({'is_post_processed': True})
    
    def ebiz_add_invoice_payment(self):
        try:
            if self.state == "posted" and self.reconciled_invoice_ids and self.payment_transaction_id:
                invoice_id = self.reconciled_invoice_ids[0]
                if not invoice_id.ebiz_internal_id:
                    invoice_id.sync_to_ebiz()
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                trans_id = self.payment_transaction_id

                if not trans_id:
                    return False

                params = {
                    'securityToken': ebiz._generate_security_json(),
                    'payment':{
                        'CustomerId': self.partner_id.id,
                        'InvoicePaymentDetails':{
                            'InvoicePaymentDetails':[
                                {
                                'InvoiceInternalId': invoice_id.ebiz_internal_id,
                                'PaidAmount': trans_id.amount,
                                }
                            ]
                        },
                        'TotalPaidAmount': trans_id.amount,
                        'CustNum': invoice_id.partner_id.ebizcharge_customer_token,
                        'RefNum': trans_id.acquirer_reference,
                        'PaymentMethodType': 'CreditCard' if trans_id.payment_token_id.token_type == 'credit' else 'ACH',
                        'PaymentMethodId': trans_id.payment_token_id.id,
                    }
                }
                resp = ebiz.client.service.AddInvoicePayment(**params)
                if resp['StatusCode'] == 1:
                    self.payment_internal_id = resp['PaymentInternalId']
                    mark_resp = ebiz.client.service.MarkPaymentAsApplied(**{
                            'securityToken': ebiz._generate_security_json(),
                            'paymentInternalId': self.payment_internal_id,
                            'invoiceNumber': invoice_id.name
                            })
                return resp
        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def js_flush_customer(self, *args, **kwargs):
        if kwargs['customers'] and  kwargs['customers'][0] == None:
            self.env['payment.token'].search([('create_uid', '=', self.env.user.id)]).with_context(
                {'donot_sync': True}).unlink()

        elif len(kwargs['customers']) > 0:
            customer = self.env['res.partner'].browse(kwargs['customers']).exists()
            if customer:
                customer.payment_token_ids.filtered(lambda x: x.create_uid == self.env.user).with_context({'donot_sync': True}).unlink()

    # def action_register_payment(self):
    #     active_ids = self.env.context.get('active_ids')
    #     if len(active_ids) == 1:
    #         record = self.env['account.move'].search([('id', '=', self.env.context.get('active_ids')[0])])
    #         if record.payment_state == "paid":
    #             raise UserError("You can't register a payment because there is nothing left to pay on the selected journal items.")
    #
    #     return super(AccountPayments, self).action_register_payment()

# class AccountPaymentRegister(models.TransientModel):
#     _inherit = "account.payment.register"
#
#     def _get_journal(self):
#         domain = [('id', '=', -1)]
#         journal_list = []
#         odoo_journals = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))])
#         for journal in odoo_journals:
#             if journal.name != 'EBizCharge':
#                 journal_list.append(journal.id)
#         if journal_list:
#             domain = [('id', 'in', journal_list)]
#             return domain
#         return domain
#
#     journal_id = fields.Many2one('account.journal', required=True, domain=_get_journal)

