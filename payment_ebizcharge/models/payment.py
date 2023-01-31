# coding: utf-8

from werkzeug import urls
from datetime import datetime
import logging
from odoo import _, api, fields, models
from odoo.addons.payment_ebizcharge.controllers.main import EbizchargeController
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class PaymentAcquirerEbizcharge(models.Model):
    _inherit = 'payment.acquirer'

    # ebizcharge_invoice_last_sync = fields.Datetime(string='Invoice Last Sync Date', readonly=True)
    provider = fields.Selection(selection_add=[('ebizcharge', 'EBizCharge')], ondelete={'ebizcharge': 'set default'})
    VALIDATION_AMOUNTS = {
        'CAD': 0.05,
        'EUR': 0.05,
        'GBP': 0.05,
        'JPY': 0.05,
        'AUD': 0.05,
        'NZD': 0.05,
        'CHF': 0.05,
        'HKD': 0.05,
        'SEK': 0.05,
        'DKK': 0.05,
        'PLN': 0.05,
        'NOK': 0.05,
        'HUF': 0.05,
        'CZK': 0.05,
        'BRL': 0.05,
        'MYR': 0.05,
        'MXN': 0.05,
        'ILS': 0.05,
        'PHP': 0.05,
        'TWD': 0.05,
        'USD': 0.05
    }

    def _get_ebizcharge_urls(self, environment):
        """ EBizCharge URLS """
        return {
            'ebizcharge_form_url': '/payment/ebizcharge',
        }

    def ebizcharge_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_ebizcharge_urls(environment)['ebizcharge_form_url']

    def get_acquirer_name(self, *args):
        if self.name == 'EBizCharge':
            return True
        else:
            return False

    @api.model
    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerEbizcharge, self)._get_feature_support()
        res['authorize'].append('ebizcharge')
        res['tokenize'].append('ebizcharge')
        return res

    @api.model
    def ebizcharge_s2s_form_process(self, data):
        if 'cardData' in data:
            exp_date = data['cardData']["expiry"].split('/')
            default = False
            if 'default_card_method' in data['cardData']:
                default = True if data['cardData']['default_card_method'] == 'true' else False
            update_data = {
                "card_exp_year": str(2000 + int(exp_date[1])),
                "card_exp_month": str(int(exp_date[0])),
                "card_code": data['cardData']["cardCode"],
                "avs_street": data['cardData']["street"],
                "avs_zip": data['cardData']["zip"],
                "account_holder_name": data['cardData']["name"],
                "is_default": default
            }
        else:
            default = False
            if 'default_account_method' in data['bankData']:
                default = True if data['bankData']['default_account_method'] == 'true' else False
            update_data = {
                "routing": data['bankData']['routingNumber'],
                "account_holder_name": data['bankData']["nameOnAccount"],
                "account_type": data['bankData']['accountType'],
                "is_default": default
            }

        if data.get('update_pm_id'):
            payment_token = self.env['payment.token'].sudo().browse(int(data.get('update_pm_id')))
            payment_token.write(update_data)
            return payment_token
        else:
            if 'cardData' in data:
                last4 = data['cardData'].get('cardNumber', "")[-4:]
                update_data.update({
                    "card_exp_year": str(2000 + int(exp_date[1])),
                    "card_exp_month": str(int(exp_date[0])),
                    "partner_id": int(data['partner_id']),
                    'name': 'XXXXXXXXXXXX%s' % last4,
                    'acquirer_ref': data['cardData']["name"],
                    'acquirer_id': int(data['acquirer_id']),
                    "card_number": data['cardData']["cardNumber"].replace(" ", ""),
                    "avs_street": data['cardData']["street"],
                    "avs_zip": data['cardData']['zip']
                })
                resp = self.sudo().ebizcharge_token_validate(update_data)
            else:
                last4 = data['bankData'].get('accountNumber', "")[-4:]
                update_data.update({
                    "acquirer_id": int(data['acquirer_id']),
                    'name': 'XXXXXXXXXXXX%s' % last4,
                    "account_number": data['bankData']['accountNumber'],
                    "routing": data['bankData']['routingNumber'],
                    "partner_id": int(data['partner_id']),
                    "token_type": "ach"
                })
            payment_token = self.env['payment.token'].sudo().create(update_data)

        return payment_token

    def ebizcharge_s2s_form_validate(self, data):
        error = dict()
        if 'bankData' in data:
            mandatory_fields = ["accountNumber", "routingNumber", "nameOnAccount", "accountType"]
            if len(data['bankData']['accountNumber']) < 4 or len(data['bankData']['accountNumber']) > 17 or len(
                    data['bankData']['routingNumber']) > 9 or len(data['bankData']['routingNumber']) < 9:
                return False
            # Checking for mandatory fields
            for field_name in mandatory_fields:
                if not data['bankData'].get(field_name):
                    error[field_name] = 'missing'
        if 'cardData' in data:
            mandatory_fields = ["cardNumber", "name", "street", "expiry", "cardCode", "zip"]
            if data['cardData']['expiry'] and \
                    datetime.now().strftime('%y%m') > datetime.strptime(data['cardData']['expiry'], '%m / %y').strftime(
                '%y%m'):
                return False
            # Checking for mandatory fields
            for field_name in mandatory_fields:
                if not data['cardData'].get(field_name):
                    error[field_name] = 'missing'

        return False if error else True

    def ebizcharge_token_validate(self, data):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj(self.env.context.get('website'))
            params = {
                "securityToken": ebiz._generate_security_json(),
                "tran": {
                    "IgnoreDuplicate": False,
                    "IsRecurring": False,
                    "Software": 'Odoo CRM',
                    "CustReceipt": False,
                    "Command": 'AuthOnly',
                    "Details": self.transaction_details(),
                    # "CustomerID": self.partner_id.id,
                    "CreditCardData": self._get_credit_card_transaction(data),
                    "AccountHolder": data['account_holder_name']
                }
            }
            resp = ebiz.client.service.runTransaction(**params)
            resp_void = ebiz.execute_transaction(resp['RefNum'], {'command': 'Void'})
        except  Exception as e:
            _logger.exception(e)
            raise ValidationError(e)
        return resp

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

    def _get_credit_card_transaction(self, data):
        return {
            'InternalCardAuth': False,
            'CardPresent': True,
            'CardNumber': data.get('card_number'),
            "CardExpiration": "%02d%s" % (int(data.get('card_exp_month')), data.get('card_exp_year')[2:]),
            'CardCode': data.get('card_code'),
            'AvsStreet': data.get('avs_street'),
            'AvsZip': data.get('avs_zip')
        }

    def ebizcharge_form_generate_values(self, values):
        self.ensure_one()
        # State code is only supported in US, use state name by default
        # See https://developer.ebizcharge.net/docs/
        state = values['partner_state'].name if values.get('partner_state') else ''
        if values.get('partner_country') and values.get('partner_country') == self.env.ref('base.us', False):
            state = values['partner_state'].code if values.get('partner_state') else ''
        billing_state = values['billing_partner_state'].name if values.get('billing_partner_state') else ''
        if values.get('billing_partner_country') and values.get('billing_partner_country') == self.env.ref('base.us', False):
            billing_state = values['billing_partner_state'].code if values.get('billing_partner_state') else ''

        config = self.env['res.config.settings'].default_get([])
        security_key = config.get('ebiz_security_key')
        user_id = config.get('ebiz_user_id')
        password = config.get('ebiz_password')

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template = self.env['email.templates'].search([])[0]
        docType = ""
        invoiceNumber = values['reference'].split('-')[0]
        if 'INV' in invoiceNumber:
            docType = 'Invoice'
        else:
            docType = 'Sales order'
        ebizcharge_tx_values = dict(values)
        temp_ebizcharge_tx_values = {
            'SecurityId': security_key,
            'UserId': user_id,
            'Password': password,
            'FormType': 'EmailForm',
            'FromEmail': values['partner'].create_uid.email,
            'FromName': values['partner'].create_uid.name,
            'EmailSubject': template.template_subject,
            'EmailAddress': values['partner'].email,
            'EmailTemplateID': template.template_id,
            'EmailTemplateName': template.name,
            'ShowSavedPaymentMethods': True,
            'CustFullName': values['partner'].name,
            'TotalAmount': values['amount'],
            'AmountDue': values['amount'],
            'CustomerId': values['partner'].ebiz_customer_id or values['partner'].id,
            'ShowViewInvoiceLink': True,
            'SendEmailToCustomer': False,
            'TaxAmount': '0',
            'SoftwareId': 'Odoo CRM',
            'Description': docType,
            'DocumentTypeId': docType,
            'InvoiceNumber': invoiceNumber,
            'TransactionLookupKey': values['reference'],
            "FirstName": values['billing_partner_name'],
            "LastName": '',
            "Address1": values['billing_partner_address'],
            "City": values['billing_partner_city'],
            "State": billing_state,
            "ZipCode": values['billing_partner_zip'],
            "Country": values['billing_partner_country'].code,
            'ApprovedURL': urls.url_join(base_url, EbizchargeController._approved_url),
            'DeclinedURL': urls.url_join(base_url, EbizchargeController._decline_url),
            'ErrorURL': urls.url_join(base_url, EbizchargeController._error_url),
            'DisplayDefaultResultPage': '0',
        }
        ebizcharge_tx_values.update(temp_ebizcharge_tx_values)
        return ebizcharge_tx_values

    def s2s_process(self, data):
        cust_method_name = '%s_s2s_form_process' % (self.provider)
        if not self.s2s_validate(data):
            return False
        if hasattr(self, cust_method_name):
            # As this method may be called in JSON and overridden in various addons
            # let us raise interesting errors before having strange crashes
            if not data.get('partner_id'):
                raise ValueError(_('Missing partner reference when trying to create a new payment token'))
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    def s2s_validate(self, data):
        cust_method_name = '%s_s2s_form_validate' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)


class PaymentTransaction(models.Model):
    _inherit = ['payment.transaction', 'ebiz.charge.api']

    _name = 'payment.transaction'

    _ebizcharge_valid_tx_status = 1
    _ebizcharge_pending_tx_status = 4
    _ebizcharge_cancel_tx_status = 2

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    ebiz_auth_code = fields.Char('Auth Code')
    security_code = fields.Char("Security Code")

    @api.model
    def create(self, vals):
        # # The reference is used in the Authorize form to fill a field (invoiceNumber) which is
        # # limited to 20 characters. We truncate the reference now, since it will be reused at
        # # payment validation to find back the transaction.
        # if 'reference' in vals and 'acquirer_id' in vals:
        #     if not vals['reference'] == False:
        #         acquier = self.env['payment.acquirer'].browse(vals['acquirer_id'])
        #         if acquier.provider == 'ebizcharge':
        #             vals['reference'] = vals.get('reference', '')[:20]
        #
        # if 'reference' in vals and not 'invoice_ids' in vals:
        #     if not vals['reference'] == False:
        #         vals['invoice_ids'] = [(6, 0, self.ids)]
        #     vals.pop('reference')

        trans = super(PaymentTransaction, self).create(vals)
        # prefix = trans.reference.split('-')[0]
        # if not prefix or prefix == 'tx':
        #     payment_id = trans.payment_id
        #     if payment_id and payment_id.payment_type == 'inbound' and payment_id.partner_type == 'customer':
        #         prefix = self.env['ir.sequence'].next_by_code('advance.payment.transaction', sequence_date=trans.last_state_change)
        #     if payment_id and payment_id.payment_type == 'outbound' and payment_id.partner_type == 'customer':
        #         prefix = self.env['ir.sequence'].next_by_code('advance.payment.transaction', sequence_date=trans.date)
        # # trans.reference = '-'.join([prefix, trans.reference.split('-')[1]])
        return trans

    @api.model
    def _ebizcharge_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ebizcharge, verify it and find the related
        transaction record. """
        _logger.info(data)
        reference = data.get("TransactionLookupKey")
        if not reference:
            error_msg = _('EBizCharge: received data with missing reference (%s)') % (reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        _logger.info(str(tx))
        if not tx or len(tx) > 1:
            error_msg = 'EBizCharge: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _ebizcharge_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # if self.acquirer_reference and data.get('x_trans_id') != self.acquirer_reference:
        #    invalid_parameters.append(('Transaction Id', data.get('TranRefNum'), self.acquirer_reference))
        # check what is buyed
        # if float_compare(float(data.get('x_amount', '0.0')), self.amount, 2) != 0:
        #    invalid_parameters.append(('Amount', data.get('x_amount'), '%.2f' % self.amount))
        return invalid_parameters

    def _ebizcharge_form_validate(self, data):
        self.write({'state': 'done',
                    'acquirer_reference': data.get('TranRefNum'),
                    'date': fields.Datetime.now(),
                    })
        return True

    def ebizcharge_s2s_do_transaction(self, **data):
        self.ensure_one()
        command = data.get('command', 'AuthOnly')
        if self.sale_order_ids:
            config = self.env['res.config.settings'].default_get([])
            if config.get('ebiz_website_allowed_command') == 'pre-auth':
                command = "AuthOnly"
            else:
                command = "Sale"
            if self.security_code:
                resp = self.sale_order_ids.run_ebiz_transaction(self.payment_token_id, command)
            else:
                resp = self.sale_order_ids.run_ebiz_transaction(self.payment_token_id, command)
            resp['x_type'] = 'capture' if command == "Sale" else command
        elif self.invoice_ids:
            if self.env.context.get('run_transaction'):
                resp = self.invoice_ids.with_context({'run_transaction': True}).run_ebiz_transaction(self.payment_token_id, command, data['card'])
            else:
                resp = self.invoice_ids.run_ebiz_transaction(self.payment_token_id, command)
            resp['x_type'] = command
        else:
            ebiz = self.get_ebiz_charge_obj()
            resp = ebiz.run_transaction_without_invoice(self)
            resp['x_type'] = 'Sale'
        # else:
        #     ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        #     resp = ebiz.run_card_validate_transaction(self)
        # resp['x_type'] = command
        if self.invoice_ids and self.invoice_ids[0].move_type == 'out_refund':
            resp['x_type'] = 'refunded'
        self._ebizcharge_s2s_validate_tree(resp)
        if self.env.user._is_public():
            self.payment_token_id.write({'card_number': 'Processed'})

        return resp

    # def _compute_reference_prefix(self, values):
    #     import pdb
    #     pdb.set_trace()
    #     prefix = super(PaymentTransaction, self)._compute_reference_prefix(values)

    #     if not prefix and values and values.get('payment_ids'):
    #         many_list = self.resolve_2many_commands('sale_order_ids', values['sale_order_ids'], fields=['name'])
    #         return ','.join(dic['name'] for dic in many_list)
    #     return prefix
    
    def ebizcharge_s2s_capture_transaction(self):
        # self.ensure_one()
        for trans in self:
            sale_order_ids = trans.sale_order_ids
            ebiz = sale_order_ids.get_ebiz_charge_obj(sale_order_ids.website_id)
            tree = ebiz.capture_transaction(trans)
            tree['x_type'] = 'capture'
            is_validated = trans._ebizcharge_s2s_validate_tree(tree)
        return is_validated

    def ebizcharge_s2s_void_transaction(self):
        self.ensure_one()
        sale_order_ids = self.sale_order_ids
        ebiz = sale_order_ids.get_ebiz_charge_obj()
        tree = ebiz.void_transaction(self)
        tree['x_type'] = 'void'
        return self._ebizcharge_s2s_validate_tree(tree)

    def ebizcharge_s2s_do_refund(self, **kwargs):
        self.ensure_one()
        ebiz = self.get_ebiz_charge_obj()
        kwargs["ref_num"] = self.acquirer_reference
        resp = ebiz.return_transaction(**kwargs)
        resp['x_type'] = "refunded"
        return self._ebizcharge_s2s_validate_tree(resp)
    
    def _ebizcharge_s2s_validate_tree(self, tree):
        return self._ebizcharge_s2s_validate(tree)

    def _ebizcharge_s2s_validate(self, tree, command="authorized"):
        self.ensure_one()
        # if self.state in ['done', 'refunded']:
        #     raise ValidationError('Your Are Trying to do operation')
        #     _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % self.reference)
        #     return True
        init_state = self.state
        if tree['ResultCode'] == "E":
            error = tree['Error']
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree['RefNum'],
                'ebiz_auth_code': tree['RefNum'],
            })
            return False
        if tree['ResultCode'] == "A":
            if tree['x_type'] in ['AuthOnly', 'sale', 'Sale']:
                self.write({
                    'acquirer_reference': tree['RefNum'],
                    'ebiz_auth_code': tree['AuthCode'],
                    'date': fields.Datetime.now(),
                })

                self._set_transaction_authorized()
                self._set_transaction_done()
                # super(PaymentTransaction, self).action_capture()
                return True
                # if init_state != 'authorized':
                #     self.execute_callback()
            if tree['x_type'] in ['capture','Check']:
                self.write({
                    'acquirer_reference': tree['RefNum'],
                    'ebiz_auth_code': tree['AuthCode'],
                })
                self._set_transaction_done()
            if tree['x_type'] == 'void':
                self._set_transaction_cancel()
            if tree['x_type'] == 'refunded':
                self.write({
                    'acquirer_reference': tree['RefNum'],
                    'ebiz_auth_code': tree['AuthCode'],
                })
                self._set_transaction_done()

            return True
                
        if tree['ResultCode'] in ["D", "E"]:
            self.write({
                'state': 'error',
                'acquirer_reference': tree['RefNum'],
                'ebiz_auth_code': tree['AuthCode'],
            })
            self._set_transaction_error(msg=tree['Error'])
            return False

    def _set_transaction_authorized(self):
        trans_type = "Authorized"  
        self._ebiz_create_application_transaction(trans_type)
        return super(PaymentTransaction, self)._set_transaction_authorized()

    def _set_transaction_done(self):
        if self.state == 'authorized':
            trans_type = "Captured"
        else:
            trans_type = "Sale"
        self._ebiz_create_application_transaction(trans_type)
        return super(PaymentTransaction, self)._set_transaction_done()
    
    def _set_transaction_cancel(self):
        if self.state == 'authorized':
            trans_type = 'Voided'
            self._ebiz_create_application_transaction(trans_type)
        return super(PaymentTransaction, self)._set_transaction_cancel()

    def _ebiz_create_application_transaction(self, trans_type):
        if self.sale_order_ids:
            if self.sale_order_ids.website_id:
                params = {
                    "partner_id": self.sale_order_ids[0].partner_id.id,
                    "sale_order_id": self.sale_order_ids[0].id,
                    "transaction_id": self.id,
                    "transaction_type": trans_type
                }
                app_trans = self.env['ebiz.application.transaction'].create(params)

                if self.sale_order_ids.ebiz_internal_id:
                    app_trans.ebiz_add_application_transaction()
        return True


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    @api.model
    def year_selection(self):
        today = fields.Date.today()
        # year =  # replace 2000 with your a start year
        year = 2000
        max_year = today.year + 30
        year_list = []
        while year != max_year: # replace 2030 with your end year
            year_list.append((str(year), str(year)))
            year += 1
        return year_list

    @api.model
    def month_selection(self):
        m_list = []
        for i in range(1,13):
            m_list.append((str(i), str(i)))
        return m_list

    @api.model
    def get_card_type_selection(self):
        icons = self.env['payment.icon'].search([]).read(['name'])
        sel = [(i['name'][0], i['name']) for i in icons]
        return sel

    ebizcharge_profile = fields.Char(string='EbizCharge Profile ID', help='This contains the unique reference '
                                                                             'for this partner/payment token combination in the Authorize.net backend')
    provider = fields.Selection(string='Provider', related='acquirer_id.provider')
    # save_token = fields.Selection(string='Save Cards', related='acquirer_id.save_token')
    account_holder_name = fields.Char('Account Holder Name *')
    card_number = fields.Char('Card Number')
    card_expiration = fields.Date('Expiration Date')
    card_exp_year = fields.Selection(year_selection, 'Expiration Year')
    card_exp_month = fields.Selection(month_selection, 'Expiration Month')
    avs_street = fields.Char("Billing Address *")
    avs_zip = fields.Char('Zip / Postal Code *')
    card_code = fields.Char('Security Code')
    card_type = fields.Char('card type')
    is_default = fields.Boolean('Is Default')
    ebiz_internal_id = fields.Char("Ebiz Charge Internal Id")
    token_type = fields.Selection([('credit', 'Credit Card'),('ach', 'ACH')], "Token Type", default="credit")
    # card_type = fields.Selection(get_card_type_selection)
    account_number = fields.Char("Account Number")
    # drivers_license = fields.Char("Drivers License")
    # drivers_license_state = fields.Char("Drivers License State")
    account_type = fields.Selection([('Checking', 'Checking'),(
        'Savings','Savings')], "Account Type *", default="Checking")
    routing = fields.Char('Routing Number', )
    card_exp_date = fields.Char('Expiration Date', compute = "_compute_card_exp_date")
    user_id = fields.Many2one('res.users')
    payment_method_icon = fields.Many2one('payment.icon')
    image = fields.Binary("Image", related="payment_method_icon.image", max_width=50, max_height=25)
    card_number_ecom = fields.Char('Card Number')
    account_number_ecom = fields.Char('Card Number')

    # @api.depends('card_exp_month', 'card_exp_year')
    def _compute_card_exp_date(self):
        for card in self:
            if card.token_type == "credit":
                card.card_exp_date = f"{card.card_exp_month}/{card.card_exp_year}"
            else:
                card.card_exp_date = ""

    @api.model
    def get_payment_token_information(self, pm_id):
        ebiz = self.browse(pm_id)
        return ebiz.read()[0]

    @api.model
    def default_get(self, fields):
        res = super(PaymentToken, self).default_get(fields)
        if self.env.context.get('default_is_ebiz_charge'):
            res['acquirer_id'] = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id
        return res

    def sync_credit_card(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj(self.env.context.get('website'))
        for profile in self:
            if profile.partner_id.ebiz_internal_id:
                if profile.ebizcharge_profile:
                    ebiz.update_customer_payment_profile(profile)
                    if profile.is_default:
                        profile.make_default()
                else:
                    res = ebiz.add_customer_payment_profile(profile)
                    last4 = profile.card_number[-4:]
                    card_number = 'XXXXXXXXXXXX%s' % last4
                    profile.write({
                        'ebizcharge_profile': res,
                        'acquirer_ref': res,
                        'card_number': card_number,
                        'name': card_number
                    })
                    if profile.is_default:
                        profile.make_default()

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        if not get_merchant_data:
            domain += [('token_type', '=', 'credit')]
        not_active = self.env['res.users'].sudo().search([('active', '=', False)])
        if not_active:
            domain += [('create_uid', 'not in', not_active.ids)]

        if 'tree_view_ref' in self.env.context and self.env.context['tree_view_ref'] == 'payment_ebizcharge.payment_token_multiple_view_credit_note':
            domain += [('token_type', '=', 'credit')]

        return super(PaymentToken, self).search_read(domain, fields, offset, limit, order)

    def sync_ach(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj(self.env.context.get('website'))
        for profile in self:
            if profile.partner_id.ebiz_internal_id:
                if profile.ebizcharge_profile:
                    resp = ebiz.update_customer_payment_profile(profile, p_type="bank")
                    if profile.is_default:
                        profile.make_default()
                    return resp
                else:
                    res = ebiz.add_customer_payment_profile(profile, p_type="bank")
                    last4 = profile.account_number[-4:]
                    profile.write({
                        'ebizcharge_profile': res,
                        'acquirer_ref': res,
                        'name': "XXXXXXXXXXXX%s" % last4,
                        'account_number': "XXXXXXXXXXXX%s" % last4
                    })
                    if profile.is_default:
                        profile.make_default()

                    return res

    def do_syncing(self):
        try:
            if self.env.user._is_public():
                return
            for token in self:
                if not token.partner_id.ebiz_internal_id or not token.partner_id.ebizcharge_customer_token:
                    token.partner_id.sync_to_ebiz()
                if token.token_type == 'ach':
                    return token.sync_ach()
                else:
                    return token.sync_credit_card()
        except Exception as e:
            raise ValidationError(str(e))
    
    def process_payment(self):
        payment_obj = {
            "partner_id": self.partner_id.id,
            "amount": self.amount_total,
        }
        wiz = self.env['wizard.order.process.transaction'].create(payment_obj)
        action = self.env.ref('payment_ebizcharge.action_process_ebiz_transaction').read()[0]
        action['res_id'] = wiz.id
        return action
    
    def create(self, values):
        if type(values) == list:
            for value in values:
                if 'acquirer_ref' not in value:
                    value['acquirer_ref'] = "Temp"
        else:
            if 'acquirer_ref' not in values:
                values['acquirer_ref'] = "Temp"
        profile = super(PaymentToken, self).create(values)
        try:
            if profile.acquirer_id.id == self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id:
                if not self.env.context.get('donot_sync'):
                    profile.do_syncing()
                    if not self.env.user._is_public():
                        profile.get_card_type()

        except Exception as e:
            _logger.exception(e)
            if len(e.args) == 2 and 'Invalid Card Number' in e.args[0]:
                raise ValidationError('You have entered invalid card number!')
            else:
                raise ValidationError(str(e))
        return profile

    def write(self, values):
        if len(values) == 1 and 'card_code' in values:
            return super(PaymentToken, self).write(values)
        check = self.partner_id.payment_token_ids.filtered(lambda x: x.is_default)
        res = super(PaymentToken, self).write(values)
        if self._ebiz_check_update_sync(values):
            if not self.env.context.get('donot_sync'):
                self.do_syncing()

        return res
    
    def save_form(self):
        if self.is_default:
            self.onchange_make_default()

    def onchange_make_default(self):
        self.partner_id.payment_token_ids.filtered(lambda x: x.is_default).update({'is_default': False})
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        
        if not self.ebizcharge_profile:
            raise UserError('Customer Might Have not Be Synced!')
        resp = ebiz.client.service.SetDefaultCustomerPaymentMethodProfile(**{
            'securityToken': ebiz._generate_security_json(),
            'customerToken': self.partner_id.ebizcharge_customer_token,
            'paymentMethodId': self.ebizcharge_profile
            })
        self.update({'is_default': True})
        return True

    def make_default(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.SetDefaultCustomerPaymentMethodProfile(**{
            'securityToken': ebiz._generate_security_json(),
            'customerToken': self.partner_id.ebizcharge_customer_token,
            'paymentMethodId': self.ebizcharge_profile
        })
        # self.write({'is_default': True})
        return resp

    def get_default_method(self):
        for method in self:
            if method.is_default:
                return method

        return self[0]

    def _ebiz_check_update_sync(self, values):
        update_check_fields = ["account_holder_name", "card_number", "card_exp_year", "card_exp_month", "avs_street",
                               "avs_zip", "card_code", "account_type", "is_default"]
        for uc_field in update_check_fields:
            if uc_field in values:
                return True
        return False

    def checkProfile(self, token):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        try:
            resp = ebiz.client.service.GetCustomerPaymentMethodProfile(**{
                'securityToken': ebiz._generate_security_json(),
                'customerToken': token.partner_id.ebizcharge_customer_token,
                'paymentMethodId': token.ebizcharge_profile
            })
            if resp:
                return True
        except:
            return False

    def unlink(self):
        if not self.env.context.get('donot_sync'):
            for token in self:
                if self.sudo().checkProfile(token):
                    try:
                        token.sudo().delete_payment_method()
                        anotherTokens = self.env['payment.token'].search([('ebizcharge_profile', '=', token.ebizcharge_profile),
                                                                          ('id', '!=', token.id)])
                        if anotherTokens:
                            for anotherToken in anotherTokens:
                                anotherToken.with_context({'donot_sync': True}).unlink()
                    except Exception as e:
                        _logger.exception(e)
        return super(PaymentToken, self).unlink()

    def delete_payment_method(self):
        """
        Author: Kuldeep
        delete the customer method form server
        """
        if self.ebizcharge_profile:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            resp = ebiz.client.service.DeleteCustomerPaymentMethodProfile(**{
                'securityToken': ebiz._generate_security_json(),
                'customerToken': self.partner_id.ebizcharge_customer_token,
                'paymentMethodId': self.ebizcharge_profile
                })
            return resp

    def delete_token(self):
        # text = "Are you sure you want to delete this {}?".format(
        #     'Credit Card' if self.token_type == 'card' else 'ACH' )
        text = "Are you sure you want to delete this payment method?"
        wizard = self.env['wizard.token.delete.confirmation'].create({"record_id": self.id,
                                                            "record_model": self._name,
                                                            "text":text})
        action = self.env.ref('payment_ebizcharge.wizard_delete_token_action').read()[0]
        action['res_id'] = wizard.id
        return action

    def open_edit(self):
        if self.token_type == "credit":
            title = 'Edit Credit Card'
            view_id = self.env.ref('payment_ebizcharge.payment_token_credit_card_view_form').id
        else:
            title = 'Edit Bank Account'
            view_id = self.env.ref('payment_ebizcharge.payment_token_ach_view_form').id

        return {
            'name': (title),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payment.token',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context
        }

    def update_payment_token(self):
        try:
            if self.is_default:
                check = self.partner_id.payment_token_ids.filtered(lambda x: x.is_default and x.id != self.id and x.create_uid == self.env.user)
                if check:
                    self.is_default = False
                    check.make_default()
                    check_or_card = "credit card" if check.token_type == "credit" else "ACH"
                    message = 'A payment method is already selected as default! Do you want to mark this one as default instead?'
                    wiz = self.env['wizard.validate.default'].create({'token_id': self.id, 'text': message, 'default_token_id': check[0].id})
                    action = self.env.ref('payment_ebizcharge.action_wizard_validate_default').read()[0]
                    action['res_id'] = wiz.id
                    return action
                else:
                    self.make_default()

            return message_wizard('Record has been successfully updated!')

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def get_card_type(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        for card in self:
            resp = ebiz.client.service.GetCustomerPaymentMethodProfile(**{
                'securityToken': ebiz._generate_security_json(),
                'customerToken': card.partner_id.ebizcharge_customer_token,
                'paymentMethodId': card.ebizcharge_profile
                })
            if resp:
                card.write({'card_type': resp['CardType']})

    def name_get(self):
        try:
            res = []
            card_types = self.get_card_type_selection()
            card_types = {x[0]: x[1] for x in card_types}
            for record in self:
                name = record.name
                if record.card_type and record.card_type != 'Unknown':
                    c_type = card_types['D' if record.card_type == 'DS' else record.card_type]
                    if name:
                        name = name.replace('XXXXXXXXXXXX', f"{c_type} Ending in ")
                name = (name or "") + ' ({})'.format("Card" if record.token_type == 'credit' else record.account_type)
                res.append((record.id, name))
            return res

        except Exception as e:
            raise ValidationError(str(e))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        odooToken = self.env['payment.token'].search([('user_id', '=', self.env.user.id),
                                                      ('partner_id', '=', args[0][-1])])
        if not odooToken:
            for arg in args:
                if 'partner_id' in arg:
                    odooPartner = self.env['res.partner'].browse(arg[-1]).exists()
                    for cust in odooPartner:
                        cust.sudo().with_context({'donot_sync': True}).ebiz_get_payment_methods()

        for arg in args:
            if 'acquirer_id.journal_id' in arg:
                odooJournal = self.env['account.journal'].search([('id', '=', arg[-1])])
                if odooJournal.name == 'EBizCharge':
                    args.append(['create_uid', 'in', [self.env.user.id]])
                    # config = self.env['res.config.settings'].sudo().default_get([])
                    # get_merchant_data = config.get('merchant_data')
                    # if not get_merchant_data:
                    #     args.append(['token_type', '=', 'credit'])
        return super(PaymentToken, self).name_search(name=name, args=args, operator=operator, limit=limit)

    def test_method(self):
        odooCards = self.env['payment.token'].search([])
        if len(odooCards) == 0:
            self.env['ir.config_parameter'].set_param('payment_ebizcharge.data_flushed', True)

    def checkRecord(self, *args, **kwargs):
        odooRecord = self.env['payment.token'].search([('id', '=', kwargs['id'])])
        if odooRecord:
            return True
        else:
            return False


class PaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"
    _description = "Generate Payment Link"

    @api.model
    def default_get(self, fields):
        res_model = self._context.get('active_model')
        if res_model == 'account.move':
            res_id = self._context.get('active_id')
            odooInvoice = self.env[res_model].search([('id', '=', res_id), ('state', '=', 'draft')])
            if odooInvoice:
                odooInvoice.action_post()
        res = super(PaymentLinkWizard, self).default_get(fields)
        return res