
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .ebiz_charge import EbizChargeAPI
from odoo.exceptions import ValidationError


class EbizChargeApi(models.AbstractModel):
    _name = "ebiz.charge.api"

    """
    this model is inherited by all the model which will be integrate with ebizcharge
    """

    def get_ebiz_charge_obj(self, website_id=None):
        """
        Kuldeep implementation
        Initalize the ebizcharge object this 
        """

        if website_id:
            credentials = self.get_website_credentials(website_id)
        else:
            credentials = self.get_crm_credentials()
        # if not 'login' in self._context:
        if not credentials[0] and not 'login' in self._context:
            raise ValidationError(f'Dear "{self.env.user.name}," You Have Not Entered The Ebiz Credentials!')

        ebiz = EbizChargeAPI(*credentials)

        return ebiz

    def get_crm_credentials(self):
        config = self.env['res.config.settings'].default_get([])
        # security_key = self.env['ir.config_parameter'].get_param('payment_ebizcharge.ebiz_security_key')
        # user_id = self.env['ir.config_parameter'].get_param('payment_ebizcharge.ebiz_user_id')
        # password = self.env['ir.config_parameter'].get_param('payment_ebizcharge.ebiz_password')
        if 'ebiz_security_key' in config:
            security_key = config.get('ebiz_security_key')
            user_id = config.get('ebiz_user_id')
            password = config.get('ebiz_password')
            return security_key, user_id, password
        else:
            security_key = config.get('ebiz_security_key_web_def')
            user_id = config.get('ebiz_user_id_web_def')
            password = config.get('ebiz_password_web_def')
            return security_key, user_id, password

    def get_website_credentials(self, website_id):
        website_id = website_id if type(website_id) == int else website_id.id
        website = self.env['website'].sudo().browse(website_id)
        if website:
            if website.ebiz_use_defaults:
                odooWebsite = self.env['website'].sudo().search([('ebiz_default', '=', True)])
                if odooWebsite:
                    return odooWebsite.ebiz_security_key, odooWebsite.ebiz_user_id, odooWebsite.ebiz_password
                else:
                    return None, None, None
            else:
                if website.ebiz_security_key:
                    return website.ebiz_security_key, website.ebiz_user_id, website.ebiz_password
                else:
                    odooWebsite = self.env['website'].sudo().search([('ebiz_default', '=', True)])
                    if odooWebsite:
                        return odooWebsite.ebiz_security_key, odooWebsite.ebiz_user_id, odooWebsite.ebiz_password
                    else:
                        return None, None, None
        else:
            return None, None, None
        
