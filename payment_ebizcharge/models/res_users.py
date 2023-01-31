from odoo import models, fields, api, _


class UserCredentials(models.Model):
    _inherit = 'res.users'

    def _check_credentials(self, password, env):
        """Make all wishlists from session belong to its owner user."""

        result = super(UserCredentials, self)._check_credentials(password, env)

        config = self.env['res.config.settings'].sudo().default_get([])
        is_security_key = config.get('ebiz_security_key', False)

        if is_security_key:
            ebiz = self.env['ebiz.charge.api'].sudo().get_ebiz_charge_obj()

            # resp = ebiz.client.service.GetMerchantTransactionData(**{
            #     'securityToken': ebiz._generate_security_json()
            # })
            # print(resp)

            resp, card_verification = self.sudo().merchant_details(ebiz)

                #FIXME:By default its True for every account EnableAVSWarnings False
                # flow/process is not decided yet as per Mr.Frank & Mam Jane (Dated 18-01-22)
                # if resp['EnableAVSWarnings'] or resp['EnableCVVWarnings']:

                # if resp['EnableCVVWarnings']:
                    # if its true, we will show cvv code in the popup, else do nothing.

            # if resp['VerifyCreditCardBeforeSaving']:
            #     if resp['UseFullAmountForAVS']:
            #         card_verification = 'full-amount'
            #     else:
            #         card_verification = 'minimum-amount'
            # else:
            #     card_verification = 'no-validation'

            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.merchant_data',  True)
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.merchant_card_verification', card_verification)
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.verify_card_before_saving', resp['VerifyCreditCardBeforeSaving'])
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.use_full_amount_for_avs', resp['UseFullAmountForAVS'])
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.allow_credit_card_pay',  True)
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.enable_cvv', resp['EnableCVVWarnings'])

        web = self.env['ir.module.module'].sudo().search([('name', '=', 'website_sale')])
        if web.state == "installed":
            all_web = self.env['website'].sudo().search([])

            for web in all_web:
                if web.ebiz_security_key or web.ebiz_use_defaults:
                    ebiz = self.env['ebiz.charge.api'].sudo().with_context({'login': True}).get_ebiz_charge_obj(web)
                    resp, card_verification = self.sudo().merchant_details(ebiz)

                    if resp and card_verification:
                        web.merchant_data = resp['AllowACHPayments']
                        web.merchant_card_verification = card_verification
                        web.verify_card_before_saving = resp['VerifyCreditCardBeforeSaving']
                        web.allow_credit_card_pay = resp['AllowCreditCardPayments']
                        web.enable_cvv = resp['EnableCVVWarnings']

        return result

    def merchant_details(self, ebiz):
        try:
            resp = ebiz.client.service.GetMerchantTransactionData(**{
                'securityToken': ebiz._generate_security_json()
            })
        except:
            return None, None

        if resp['VerifyCreditCardBeforeSaving']:
            if resp['UseFullAmountForAVS']:
                return resp, 'full-amount'
            else:
                return resp, 'minimum-amount'
        else:
            return resp, 'no-validation'
