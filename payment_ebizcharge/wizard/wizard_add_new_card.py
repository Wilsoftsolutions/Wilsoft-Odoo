from odoo import fields, models,api, _
from odoo.exceptions import UserError, ValidationError, Warning
import logging
from datetime import datetime
from ..models.ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)


class WizardAddNewCard(models.TransientModel):
    _name = 'wizard.add.new.card'
    
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
        
    partner_id = fields.Many2one('res.partner')
    card_account_holder_name = fields.Char('Name on Card *')
    card_card_number = fields.Char('Card Number *')
    # card_card_expiration = fields.Date('Expiration Date')
    card_exp_year = fields.Selection(year_selection, 'Expiration Year *')
    card_exp_month = fields.Selection(month_selection, 'Expiration Month *')
    card_avs_street = fields.Char("Billing Address *")
    card_avs_zip = fields.Char('Zip / Postal Code *')
    card_card_code = fields.Char('Security Code *')
    make_default_card = fields.Boolean('Make Default')


    @api.constrains('card_card_number')
    def card_card_number_length_id(self):
        for rec in self:
            if rec.card_card_number and (len(rec.card_card_number) > 19 or len(rec.card_card_number) < 13):
                raise ValidationError(_('Card number should be valid and should be 13-19 digits!'))

    @api.constrains('card_exp_month', 'card_exp_year')
    def card_expiry_date(self):
        today = datetime.now()
        for rec in self:
            if rec.card_exp_month and rec.card_exp_year:
                if int(rec.card_exp_year) > today.year:
                        return 
                elif int(rec.card_exp_year) == today.year:
                    if int(rec.card_exp_month) >= today.month:
                        return
                raise ValidationError(_('Card expiry date must be a future date!'))
    # _sql_constraints = [
    #         (
    #             'card_card_number_length_check',
    #             'check (LENGTH(card_card_number) = 16)',
    #             ('Card Number should 16 digits')
    #         ),
    #     ]
    # def _check_card_card_number(self):
    #         if self.card_card_number:
    #             if len(self.card_card_number) == 16:
    #                 return True
    #             else:
    #                 return False
    #         return True

    # _constraints = [
    #     (_check_card_card_number, 'Credit card must have exactly 16 numbers.', ['card_card_number'])]
    
    def save_card(self):

        if self.card_avs_zip:
            if len(self.card_avs_zip) > 15:
                raise ValidationError(_('Zip / Postal Code must be less than 15 Digits!'))
            elif '-' in self.card_avs_zip:
                for mystr in self.card_avs_zip.split('-'):
                    if not mystr.isalnum():
                        raise ValidationError(_("Zip/Postal Code can only include numbers, letters, and '-'."))
            elif not self.card_avs_zip.isalnum():
                raise ValidationError(_("Zip/Postal Code can only include numbers, letters, and '-'."))

        return self.validate_card()

    def validate_card(self):
        self.ensure_one()

        config = self.env['res.config.settings'].sudo().default_get([])
        verify_card_before_saving = config.get('verify_card_before_saving')

        # if self.check_if_merchant_needs_avs_validation():

        if verify_card_before_saving:
            resp = self.credit_card_validate_transaction()
            avs_result = self.get_avs_result(resp)
            if all([x == 'Match' for x in avs_result]) and resp['ResultCode'] == 'A':
                return self.create_credit_card_payment_method_default_msg()
            return self.show_payment_response(resp)
        else:
            return self.create_credit_card_payment_method_default_msg()

    def make_default(self,current_pointer):
        default_tokens = self.partner_id.payment_token_ids.filtered(lambda x: x.is_default)
        
        if default_tokens:
            self.partner_id.payment_token_ids.filtered(lambda x: x.is_default).write({'is_default':False})

        current_pointer.write({'is_default':True})
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.SetDefaultCustomerPaymentMethodProfile(**{
            'securityToken': ebiz._generate_security_json(),
            'customerToken': self.partner_id.ebizcharge_customer_token,
            'paymentMethodId': current_pointer.ebizcharge_profile
            })
        return True

    def create_credit_card_payment_method(self):
        params = {
            "account_holder_name": self.card_account_holder_name,
            "card_number": self.card_card_number,
            "card_exp_year": str(self.card_exp_year),
            "card_exp_month": str(self.card_exp_month),
            "avs_street": self.card_avs_street,
            "avs_zip": self.card_avs_zip,
            "card_code": self.card_card_code,
            "partner_id": self.partner_id.id,
            "acquirer_ref": "Temp",
            "verified": True,
            # 'is_default': self.make_default(),
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id
        }
        
        card = self.env['payment.token'].create(params)
        # card.get_card_type()
        if self.make_default_card:
            self.make_default(card)
        return card

    def create_credit_card_payment_method_default_msg(self):
        params = {
            "account_holder_name": self.card_account_holder_name,
            "name": self.card_account_holder_name,
            "card_number": self.card_card_number,
            "card_exp_year": str(self.card_exp_year),
            "card_exp_month": str(self.card_exp_month),
            "avs_street": self.card_avs_street,
            "avs_zip": self.card_avs_zip,
            "card_code": self.card_card_code,
            "partner_id": self.partner_id.id,
            "acquirer_ref": "Temp",
            "verified": True,
            # 'is_default': self.make_default(),
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id
        }

        card = self.env['payment.token'].create(params)
        # card.get_card_type()
        if self.make_default_card:
            check = self.partner_id.payment_token_ids.filtered(
                lambda x: x.is_default and x.id != self.id and x.create_uid == self.env.user)
            if check:
                message = 'A payment method is already selected as default! Do you want to mark this one as default instead?'
                wiz = self.env['wizard.validate.default'].create(
                    {'token_id': card.id, 'text': message, 'default_token_id': check[0].id})
                action = self.env.ref('payment_ebizcharge.action_wizard_validate_default_on_create').read()[0]
                action['res_id'] = wiz.id
                return action
            else:
                self.make_default(card)
        return message_wizard('Card has been successfully saved!')

    def show_payment_response(self, resp):
        action = self.env.ref('payment_ebizcharge.action_wizard_view_add_card_validation').read()[0]
        if resp['ResultCode'] == 'E':
            raise ValidationError(resp['Error'])
        card_code, address, zip_code = self.get_avs_result(resp)

        validation_params = {'address': address,
            'zip_code': zip_code,
            'card_code': card_code,
            'wizard_prcoess_id': self.id,
            'check_avs_match': all([x == "Match" for x in [card_code, address, zip_code]])}

        if resp['ResultCode'] == 'D':
            validation_params['is_card_denied'] = True
            validation_params['denied_message'] = 'Card Declined' if 'Card Declined' in resp['Error'] else resp['Error']
            action['name'] = 'Card Declined'
        wiz = self.env['wizard.add.card.validation'].create(validation_params)
        action['res_id'] = wiz.id
        return action

    def _get_credit_card_transaction(self):
        return {
                'InternalCardAuth': False,
                'CardPresent': True,
                'CardNumber': self.card_card_number,
                "CardExpiration": "%s%s"%(self.card_exp_month, self.card_exp_year[2:]),
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

    def credit_card_validate_transaction(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            params = {
                "securityToken": ebiz._generate_security_json(),
                "tran": {
                    "IgnoreDuplicate": False,
                    "IsRecurring": False,
                    "Software":'Odoo CRM',
                    "CustReceipt": False,
                    "Command": 'AuthOnly',
                    "Details": self.transaction_details(),
                    "CustomerID": self.partner_id.id,
                    "CreditCardData": self._get_credit_card_transaction(),
                    "AccountHolder": self.card_account_holder_name,
                }
            }
            resp = ebiz.client.service.runTransaction(**params)
            resp_void = ebiz.execute_transaction(resp['RefNum'], {'command': 'Void'})
        except  Exception as e:
            _logger.exception(e)
            raise ValidationError(e)
        return resp

    def get_avs_result_old(self, resp):
        card_code = resp['CardCodeResult']
        avs = resp['AvsResult']
        if '&' in avs :
            array = avs.split('&')
            address = array[0].split(':')[1]
            zip_code = array[1].split(':')[1]
        else:
            address = avs
            zip_code = avs

        return card_code.strip(), address.strip(), zip_code.strip()

    def get_avs_result_old2(self, resp):
        card_code = resp['CardCodeResult']
        avs_code = resp['AvsResultCode']
        if avs_code:
            if avs_code in ['YYY', 'YYX', 'YNA', 'YYG', 'GGG'] :
                address = 'Match'
            if avs_code in ['YYY','NYZ', 'YYX', 'NYW']:
                zip_code = 'Match'
            if avs_code in ['NYZ', 'NNN', "NYW"]:
                address = 'No Match'
            if avs_code in ['YNA', 'NNN']:
                zip_code = 'No Match'
            if avs_code in ['XXW', 'XXU', 'XXS', 'XXS','XXS','XXR','XXE', 'XXG']:
                address = 'No Match'
                zip_code = 'No Match'

            # if avs_code == 'XXW':
            #     address = 'Card Number Not On File'
            #     zip_code = address
            # if avs_code == 'XXU':
            #     address = 'Address Information not verified for domestic transaction'
            #     zip_code = address
            # if avs_code == 'XXS':
            #     address = 'Service Not Supported'
            #     zip_code = address
            # if avs_code == 'XXS':
            #     address = 'Address Verification Not Allowed For Card Type'
            #     zip_code = address
            # if avs_code == 'XXS':
            #     address = 'Global Non-AVS participant'
            #     zip_code = address
            # if avs_code == 'XXR':
            #     address = 'Retry / System Unavailable'
            #     zip_code = address
        else:
            address = "Not Match"
            zip_code = "Not Match"

        return card_code.strip(), address.strip(), zip_code.strip()

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
        address , zip_code= 'No Match', 'No Match'

        if avs in ['YYY', 'Y', 'YYA','YYD']:
            address = zip_code = 'Match'
        if avs in ['NYZ', 'Z' ]:
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


class WizardValidateDefault(models.TransientModel):
    _name = "wizard.validate.default"

    token_id = fields.Many2one('payment.token')
    default_token_id = fields.Many2one('payment.token')
    text = fields.Text('Message', readonly=True)

    def accept_default(self):
        # self.token_id.make_default()
        self.default_token_id.is_default = False
        self.token_id.is_default = True
        return self.token_id.open_edit()

    def reject_default(self):
        self.token_id.is_default = False
        return self.token_id.open_edit()

    def accept_default_on_create(self):
        self.token_id.make_default()
        if self.token_id.token_type == 'credit':
            return message_wizard('Card has been successfully saved!')
        elif self.token_id.token_type == 'ach':
            return message_wizard('Bank account has been successfully saved!')

    def reject_default_on_create(self):
        if self.token_id.token_type == 'credit':
            return message_wizard('Card has been successfully saved!')
        elif self.token_id.token_type == 'ach':
            return message_wizard('Bank account has been successfully saved!')