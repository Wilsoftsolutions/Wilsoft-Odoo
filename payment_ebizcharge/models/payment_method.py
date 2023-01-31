# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__file__)

class EbizPaymentMethodsBank(models.Model):
    _inherit = "ebiz.charge.api"
    _name = "ebiz.payment.bank"

    # _rec_name = 'account_holder_name'

    account_holder_name = fields.Char("Account Holder Name", required=True)
    name = fields.Char('Method Name', required=True, default="New")
    account_number = fields.Char("Account #", required=True)
    # drivers_license = fields.Char("Drivers License")
    # drivers_license_state = fields.Char("Drivers License State")
    account_type = fields.Selection([('Checking', 'Checking'),(
        'Savings','Savings')], "Account Type", required=True, default="Checking")
    routing = fields.Char('Account Routing', required=True)
    partner_id = fields.Many2one('res.partner')
    ebiz_internal_id = fields.Char()
    is_default = fields.Boolean(default=False)

    def do_syncing(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        for profile in self:
            if profile.partner_id.ebiz_internal_id:
                if profile.ebiz_internal_id:
                    resp = ebiz.update_customer_payment_profile(profile, p_type = "bank")
                else:
                    res = ebiz.add_customer_payment_profile(profile, p_type = "bank")
                    last4 = profile.account_number[-4:]
                    account_number = 'XXXXXX%s' % last4
                    routing_number = "XXXXXX%s" % profile.routing[-4:]
                    profile.write({'ebiz_internal_id': res,
                                'account_number': account_number,
                                'routing': routing_number,
                                'name': account_number})

    def create(self, values):
        profile = super(EbizPaymentMethodsBank, self).create(values)
        if 'ebiz_internal_id' not in values:
            profile.do_syncing()
        return profile

    def write(self, values):
        check = self.partner_id.ebiz_ach_ids.filtered(lambda x: x.is_default)
        if check and 'is_default' in values and values['is_default']:
            raise UserError(f'Customer ACH is Already Selected As Default! Please Uncheck The \"{check.account_holder_name}\'s\" ACH Account To Continue!')

        checking_card = self.partner_id.payment_token_ids.filtered(lambda x: x.is_default)
        if checking_card and 'is_default' in values and values['is_default']:
            raise UserError(f'Customer Credit Card is Already Selected As Default! Please Uncheck The \"{checking_card.account_holder_name}\'s\" Card To Continue!')

        super(EbizPaymentMethodsBank, self).write(values)

        # for line_item in self.partner_id.ebiz_ach_ids:
        #     if not line_item.is_default:
        #         super(EbizPaymentMethodsBank, self.partner_id.ebiz_ach_ids.filtered(lambda x: not x.is_default)).write({'is_default': False})

        if self._ebiz_check_update_sync(values):
            try:
                self.do_syncing()
            except Exception as e:
                _logger.exception(e)

        # testing default now
        if 'is_default' in values and values['is_default']:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            resp = ebiz.client.service.SetDefaultCustomerPaymentMethodProfile(**{
                'securityToken': ebiz._generate_security_json(),
                'customerToken': self.partner_id.ebizcharge_customer_token,
                'paymentMethodId': self.ebiz_internal_id
            })
        return True

    def make_default(self):
        self.partner_id.ebiz_ach_ids.filtered(lambda x: x.is_default).write({'is_default':False})
        self.write({'is_default':True})
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        resp = ebiz.client.service.SetDefaultCustomerPaymentMethodProfile(**{
            'securityToken': ebiz._generate_security_json(),
            'customerToken': self.partner_id.ebizcharge_customer_token,
            'paymentMethodId': self.ebiz_internal_id
            })
        return True

    def _ebiz_check_update_sync(self, values):
        update_check_fields = ["account_holder_name", "account_type",]
        for uc_field in update_check_fields:
            if uc_field in values:
                return True
        return False

    def unlink(self):
        ebiz = self.get_ebiz_charge_obj()
        for pro in self:
            if pro.ebiz_internal_id:
                try:
                    ebiz.delete_customer_payment_profile(pro)
                except Exception as e:
                    pass
        return super(EbizPaymentMethodsBank, self).unlink()



# class EbizPaymentMethodsCreditCard(models.Model):
#     _inherit = "ebiz.charge.api"
#     _name = "ebiz.payment.credit.card"
#     _rec_name = 'card_number'
    
#     account_holder_name = fields.Char('Name on Card', required=True)
#     card_number = fields.Char('Card Number', required=True)
#     card_expiration = fields.Date('Expiration Date', required=True)
#     avs_street = fields.Char("Billing Address", required=True)
#     avs_zip = fields.Char('Zip Code', required=True)
#     card_code = fields.Char('Security Code', required=True)
#     card_type = fields.Char('Card Type')
#     partner_id = fields.Many2one('res.partner')
#     make_default = fields.Boolean(default=False)
#     payment_token_id = fields.Many2one('payment.token')
#     ebiz_internal_id = fields.Char("Ebiz Charge Internal Id")
#     is_default = fields.Boolean(default=False)

#     def do_syncing(self):
#         ebiz = self.get_ebiz_charge_obj()
#         for profile in self:
#             if profile.partner_id.ebiz_internal_id:
#                 if not profile.ebiz_internal_id:
#                     res = ebiz.add_customer_payment_profile(profile)
#                     profile.ebiz_internal_id = res

#     def create(self, values):
#         profile = super(EbizPaymentMethodsCreditCard, self).create(values)
#         try:
#             profile.do_syncing()
#             last4 = profile.card_number[-4:]
#             token = self.env['payment.token'].sudo().create({
#                 'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
#                 'partner_id': profile.partner_id.id,
#                 'ebizcharge_profile': profile.ebiz_internal_id,
#                 'name': 'XXXXXXXXXXXX%s' % last4,
#                 'acquirer_ref': profile.account_holder_name
#             })
#             profile.update({'card_number' :'XXXXXXXXXXXX%s' % last4, 'payment_token_id': token.id})

#         except Exception as e:
#             _logger.exception(e)
#         return profile

#     def write(self, values):
#         super(EbizPaymentMethodsCreditCard, self).write(values)
#         self.do_syncing()
#         return True

#     def make_default(self):
#        self.partner_id.ebiz_credit_card_ids.write({'default':False})
#        self.write({'default':False})

#     def get_default_method(self):
#         for method in self:
#             if method.is_default:
#                 return method

#         return self[0]