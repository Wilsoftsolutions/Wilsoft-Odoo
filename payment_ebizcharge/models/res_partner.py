# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning, MissingError
from zeep import Client
import logging
from datetime import datetime, timedelta
import re
from .ebiz_charge import message_wizard

_logger = logging.getLogger(__name__)

customer_time_spanm = False


class ResPartner(models.Model):
    _inherit = ["res.partner", "ebiz.charge.api"]
    _name = "res.partner"

    # ebizcharge_customer_id = fields.Char('Ebiz Customer Id', default="")
    def _get_default_ebiz_auto_sync(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        return config.get('ebiz_auto_sync_customer', False)

    def _compute_ebiz_auto_sync(self):
        self.ebiz_auto_sync = False

    # ebiz_ach_ids = fields.One2many('ebiz.payment.bank', 'partner_id', string='Ebiz ACH', copy=False)
    ebiz_ach_tokens = fields.One2many('payment.token', string='EBizCharge ACH', compute="_compute_ach", copy=False)
    ebiz_credit_card_ids = fields.One2many('payment.token', string='EBizCharge Credit Card', compute="_compute_credit_card", copy=False)
    # ebiz_credit_card_ids = fields.One2many('ebiz.payment.credit.card', 'partner_id', string='Ebiz Credit Card', copy=False)
    ebiz_internal_id = fields.Char(string='Customer Internal Id', copy=False)
    ebizcharge_customer_token = fields.Char(string='Customer Token', copy=False)
    webform_url = fields.Char(string='Url for Web form', required=False)
    ebiz_auto_sync = fields.Boolean(compute="_compute_ebiz_auto_sync", default=_get_default_ebiz_auto_sync)
    sync_status = fields.Char(string="EBizCharge Upload Status", compute="_compute_sync_status")
    #Niaz Impelementaion (For def import_ebiz_customer:)
    ebiz_customer_internal_id = fields.Char('Ebiz Customer Internal ID')
    ebiz_customer_id = fields.Char('Ebiz Customer ID')
    request_payment_method_sent = fields.Boolean('Ebiz Request payment', default=False)
    sync_response = fields.Char(string="Sync Status", copy=False)
    last_sync_date = fields.Datetime(string="Upload Date & Time", copy=False)
    payment_token_ach_count = fields.Integer('Count Payment Token', compute='_compute_payment_ach_token_count')

    ach_functionality_hide = fields.Boolean(compute="check_if_merchant_needs_avs_validation", default=False)
    card_functionality_hide = fields.Boolean(default=False)

    def check_if_merchant_needs_avs_validation(self):
        """
        Gets Merchant transaction configuration
        """
        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        get_allow_credit_card_pay = config.get('allow_credit_card_pay')

        self.ach_functionality_hide = get_merchant_data
        self.card_functionality_hide = get_allow_credit_card_pay

        # if get_merchant_data:
        #     self.ach_functionality_hide = True
        #
        # else:
        #     self.ach_functionality_hide = False

    def get_default_token(self):
        for token in self.payment_token_ids:
            if token.is_default:
                if token.token_type == "credit":
                    return token
                else:
                    return token
        return None
                
    @api.depends('payment_token_ids')
    def _compute_payment_ach_token_count(self):
        payment_data = self.env['payment.token'].read_group([
            ('partner_id', 'in', self.ids),('token_type','=','ach'),('user_id','=',self.env.user.id)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(payment['partner_id'][0], payment['partner_id_count']) for payment in payment_data])
        for partner in self:
            partner.payment_token_ach_count = mapped_data.get(partner.id, 0)
    
    @api.depends('payment_token_ids')
    def _compute_payment_token_count(self):
        payment_data = self.env['payment.token'].read_group([
            ('partner_id', 'in', self.ids),('token_type','=','credit'),('user_id','=',self.env.user.id)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(payment['partner_id'][0], payment['partner_id_count']) for payment in payment_data])
        for partner in self:
            partner.payment_token_count = mapped_data.get(partner.id, 0)

    def _compute_sync_status(self):
        for cus in self:
            if not cus.active:
                cus.sync_status = "Archieve"
            elif cus.customer_rank > 0:
                cus.sync_status = "Synchronized" if cus.ebiz_internal_id else "Pending"
            else:
                cus.sync_status = "Pending"

    def _compute_credit_card(self):
        for partner in self:
            partner.ebiz_credit_card_ids = partner.payment_token_ids.filtered(lambda x: x.token_type == 'credit' and x.create_uid == self.env.user)

    def _compute_ach(self):
        for partner in self:
            partner.ebiz_ach_tokens = partner.payment_token_ids.filtered(lambda x: x.token_type == 'ach' and x.create_uid == self.env.user)

    @api.model
    def create(self, values):
        config = self.env['res.config.settings'].default_get([])
        partner = super(ResPartner, self).create(values)
        if config.get('ebiz_auto_sync_customer'):
            if partner.customer_rank > 0 and not partner.ebiz_internal_id:
                partner.sync_to_ebiz()
        return partner

    def sync_to_ebiz_ind(self):
        self.sync_to_ebiz()
        return message_wizard('Customer uploaded successfully!')

    def sync_to_ebiz(self, time_sample=None):
        self.ensure_one()
        
        ebiz = self.get_ebiz_charge_obj(self.website_id.id if hasattr(self, 'website_id') else None)
        update_params = {}
        if self.ebiz_internal_id:
            resp = ebiz.update_customer(self)

            self.env['logs.of.customers'].create({
                'customer_name': self.id,
                'customer_id': self.id,
                'name': self.name,
                'street': self.street or "",
                'email_id': self.email or "",
                'customer_phone': self.phone or "",
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,
            })
        else:
            resp = ebiz.add_customer(self)
            # self.last_sync_date = fields.Datetime.now()
            if resp['ErrorCode'] == 0:
                update_params = {
                    'ebiz_internal_id': resp['CustomerInternalId'],
                    'ebiz_customer_id': resp['CustomerId']
                }

            self.env['logs.of.customers'].create({
                'customer_name': self.id,
                'customer_id': self.id,
                'name': self.name,
                'street': self.street or "",
                'email_id': self.email or "",
                'customer_phone': self.phone or "",
                'sync_status': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,

            })
            # self.ebiz_ach_ids.do_syncing()
            # self.payment_token_ids.do_syncing()

        token = ebiz.get_customer_token(self.id)
        update_params['ebizcharge_customer_token'] = token
        # reference_to_upload_customer = self.env['list.of.customers'].search([('customer_id', '=', self.id)])
        # reference_to_upload_customer.last_sync_date = datetime.now()
        # reference_to_upload_customer.sync_status = resp['Error'] or resp['Status']
        update_params.update({'last_sync_date': fields.Datetime.now(), 'sync_response': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error']})
        self.write(update_params)
        # self.payment_token_ids.do_syncing()
        return resp

    def view_logs(self):
        return {
            'name': (_('Customer Logs')),
            # 'domain': [('from_model', '=', 'Contacts'), ('contact_name', '=', self.id)],
            'view_type': 'form',
            'res_model': 'customer.logs',
            'target': 'new',
            'view_id': False,
            'view_mode': 'tree,pivot,form',
            'type': 'ir.actions.act_window',
        }

    def sync_multi_customers(self):

        time = datetime.now()
        set = self.env['ir.config_parameter'].set_param('payment_ebizcharge.time_spam_test', time)
        time_sample = get = self.env['ir.config_parameter'].get_param('payment_ebizcharge.time_spam_test')

        resp_lines = []
        # resp_lines.append([0, 0, {
        #             'record_name': "INV023232",
        #             'record_message': "Success"
        #         }])
        # resp_lines.append([0, 0, {
        #             'record_name': "INV02323",
        #             'record_message': "Record Already Exists"
        #         }])
        success = 0
        failed = 0
        total = len(self)
        for partner in self:
            if partner.customer_rank > 0:
                resp_line = {
                    'customer_name': partner.name,
                    'customer_id': partner.id
                }
                try:
                    resp = partner.sync_to_ebiz(time_sample)
                    resp_line['record_message'] = resp['Error'] or resp['Status']
                    # self.env['customer.logs'].create({
                    #     'sync_date': datetime.now(),
                    #     'customer_name': partner.id,
                    #     'create_update': 'Created',
                    #     'res_user': self.env.user.id,
                    #     'message_sucess': 'Success' if resp['ErrorCode'] in [0, 2] else resp['Error'],
                    #     'responce': resp.Status,
                    #     # 'init_date_time': customer_time_spanm,
                    #     'init_date_time': time_sample,
                    # })
                except Exception as e:
                    _logger.exception(e)
                    resp_line['record_message'] = str(e)

                if resp_line['record_message'] == 'Success' or resp_line['record_message'] =='Record already exists':
                    success += 1
                else:
                    failed += 1
                
                resp_lines.append([0, 0, resp_line])   


        wizard = self.env['wizard.multi.sync.message'].create({'name':'customers', 'customer_lines_ids':resp_lines,
            'success_count': success, 'failed_count': failed, 'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def sync_multi_customers_from_upload_customers(self, list):
        customer_records = self.env['res.partner'].browse(list).exists()
        resp_lines = []
        success = 0
        failed = 0
        total = len(customer_records)
        for partner in customer_records:

            if partner.customer_rank > 0:
                resp_line = {
                    'customer_name': partner.name,
                    'customer_id': partner.id
                }
                try:
                    resp = partner.sync_to_ebiz()
                    resp_line['record_message'] = resp['Error'] or resp['Status']
                except Exception as e:
                    _logger.exception(e)
                    resp_line['record_message'] = str(e)

                if resp_line['record_message'] == 'Success' or resp_line['record_message'] == 'Record already exists':
                    success += 1
                else:
                    failed += 1

                resp_lines.append([0, 0, resp_line])

        wizard = self.env['wizard.multi.sync.message'].create({'name': 'customers', 'customer_lines_ids': resp_lines,
                                                               'success_count': success, 'failed_count': failed,
                                                               'total': total})
        action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
        action['context'] = self._context
        action['res_id'] = wizard.id
        return action

    def add_new_card(self):
        """
        author: Kuldeep
        return as wizard for adding new card
        """
        if self.customer_rank > 0 and not self.ebiz_internal_id:
            self.sync_to_ebiz()

        wizard = self.env['wizard.add.new.card'].create({'partner_id':self.id,
            'card_account_holder_name': self.name,  
            # 'is_check_or_credit': 'credit',
            'card_avs_street':self.street,
            'card_avs_zip': self.zip})
        action = self.env.ref('payment_ebizcharge.action_wizard_add_new_card').read()[0]
        action['res_id'] = wizard.id
        return action

    def add_new_ach(self):
        """
        author: Kuldeep
        return as wizard for adding new ACH
        """

        if self.customer_rank > 0 and not self.ebiz_internal_id:
            self.sync_to_ebiz()

        wizard = self.env['wizard.add.new.ach'].create({'partner_id':self.id,
            'ach_account_holder_name': self.name})
        action = self.env.ref('payment_ebizcharge.action_wizard_add_new_ach').read()[0]
        action['res_id'] = wizard.id
        return action

    def ebiz_get_default_payment_methods_for_all(self):
        for customer in self:
            customer.with_context({'donot_sync': True}).ebiz_get_default_payment_methods()

    def ebiz_get_default_payment_methods(self):
        try:
            ebiz = self.get_ebiz_charge_obj()
            methods = ebiz.client.service.GetCustomerPaymentMethodProfiles(**{'securityToken': ebiz._generate_security_json(), 
                'customerToken': self.ebizcharge_customer_token})
            if not methods:
                return
            for method in methods:
                token = self.payment_token_ids.filtered(lambda x: x.ebizcharge_profile == method['MethodID'] and x.user_id == self.env.user)
                if not token and method['SecondarySort'] == '0':
                    if method['MethodType'] == 'cc':
                        self.create_card_from_ebiz_data(method)
                    else:
                        self.create_ach_from_ebiz_data(method)
                    
                    self.write({'request_payment_method_sent': False})

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    def create_card_from_ebiz_data(self, method):
        exp = method['CardExpiration'].split('-')
        params = {
            "account_holder_name": method['AccountHolderName'],
            "card_type": method['CardType'],
            "card_number":  method['CardNumber'],
            "name":  method['CardNumber'],
            "card_exp_year": exp[0],
            "card_exp_month": str(int(exp[1])),
            "avs_street": method['AvsStreet'],
            "avs_zip": method['AvsZip'],
            "card_code": method['CardCode'],
            "partner_id": self.id,
            "is_default": True if method['SecondarySort'] == '0' else False,
            "acquirer_ref": method['MethodID'],
            "ebizcharge_profile": method['MethodID'],
            "verified": True,
            "user_id": self.env.user.id,
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id
        }
        self.env['payment.token'].create(params)

    def create_ach_from_ebiz_data(self, method):
        params = {
            'account_holder_name': method['AccountHolderName'],
            'account_number': method['Account'],
            'name': method['Account'],
            # 'drivers_license': method['DriversLicense'],
            # 'drivers_license_state': method['DriversLicenseState'],
            'account_type': method['AccountType'],
            'routing': method['Routing'],
            'is_default': True if method['SecondarySort'] == '0' else False,
            'ebiz_internal_id': method['MethodID'],
            'partner_id': self.id,
            "acquirer_ref": method['MethodID'],
            "ebizcharge_profile": method['MethodID'],
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
            'token_type': 'ach',
            "user_id": self.env.user.id

        }
        self.env['payment.token'].create(params)

    @api.model
    def get_card_type_selection(self):
        icons = self.env['payment.icon'].search([]).read(['name'])
        sel = [(i['name'][0], i['name']) for i in icons]
        return sel

    def ebiz_get_payment_methods(self):
        try:
            config = self.env['res.config.settings'].sudo().default_get([])
            get_merchant_data = config.get('merchant_data')
            get_allow_credit_card_pay = config.get('allow_credit_card_pay')

            ebiz = self.get_ebiz_charge_obj()
            methods = ebiz.client.service.GetCustomerPaymentMethodProfiles(
                **{'securityToken': ebiz._generate_security_json(),
                   'customerToken': self.ebizcharge_customer_token})
            if not methods:
                return
            for method in methods:
                if method['MethodType'] == 'cc':
                    if get_allow_credit_card_pay:
                        card = self.payment_token_ids.filtered(
                            lambda x: x.ebizcharge_profile == method['MethodID'] and x.create_uid == self.env.user)
                        exp = method['CardExpiration'].split('-')
                        odooImage = ''
                        c_type = ''
                        try:
                            if method['CardType']:
                                card_types = self.get_card_type_selection()
                                card_types = {x[0]: x[1] for x in card_types}
                                c_type = card_types['D' if method['CardType'] == 'DS' else method['CardType']]
                                odooImage = self.env['payment.icon'].search([('name', '=', c_type)]).id
                        except Exception as e:
                            if e.args[0] == 'Unknown':
                                continue
                        params = {
                            "account_holder_name": method['AccountHolderName'],
                            "card_type": method['CardType'],
                            "card_number": method['CardNumber'],
                            "name": method['CardNumber'],
                            "card_exp_year": exp[0],
                            "card_exp_month": str(int(exp[1])),
                            "avs_street": method['AvsStreet'],
                            "avs_zip": method['AvsZip'],
                            "card_code": method['CardCode'],
                            "partner_id": self.id,
                            "is_default": True if method['SecondarySort'] == "0" else False,
                            "acquirer_ref": method['MethodID'],
                            "ebizcharge_profile": method['MethodID'],
                            "verified": True,
                            "user_id": self.env.user.id,
                            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
                            'payment_method_icon': odooImage,
                            'card_number_ecom': "ending in " + str(re.split('(\d+)',method['CardNumber'])[1])
                        }
                        self.write({'request_payment_method_sent': False})
                        if card:
                            card.write(params)
                        else:
                            self.env['payment.token'].create(params)
                else:
                    if get_merchant_data:
                        bank = self.payment_token_ids.filtered(
                            lambda x: x.ebizcharge_profile == method['MethodID'] and x.create_uid == self.env.user)
                        params = {
                            'account_holder_name': method['AccountHolderName'],
                            'account_number': method['Account'],
                            'name': method['Account'],
                            # 'drivers_license': method['DriversLicense'],
                            # 'drivers_license_state': method['DriversLicenseState'],
                            'account_type': method['AccountType'].capitalize(),
                            'routing': method['Routing'],
                            'is_default': True if method['SecondarySort'] == "0" else False,
                            'ebiz_internal_id': method['MethodID'],
                            'partner_id': self.id,
                            "acquirer_ref": method['MethodID'],
                            "ebizcharge_profile": method['MethodID'],
                            "user_id": self.env.user.id,
                            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
                            'token_type': 'ach',
                            'account_number_ecom': method['AccountType'].capitalize() + " ending in " + str(re.split('(\d+)',method['Account'])[1])
                        }
                        self.write({'request_payment_method_sent': False})
                        if bank:
                            bank.write(params)
                        else:
                            self.env['payment.token'].create(params)

        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))

    @api.model
    def cron_load_payment_methods(self):
        partners = self.search([('request_payment_method_sent', '=', True)])
        for partner in partners:
            partner.ebiz_get_payment_methods()

    def write(self, values):
        ret = super(ResPartner, self).write(values)
        # if self.env['ir.config_parameter'].get_param('payment_ebizcharge.ebiz_auto_sync_sale_order'):
        if self._ebiz_check_update_sync(values):
            for partner in self:
                if partner.ebiz_internal_id:
                    partner.sync_to_ebiz()
        return ret

    def ebiz_request_payment_method(self):
        try:
            ebiz = self.get_ebiz_charge_obj()

            if self.customer_rank > 0 and not self.ebiz_internal_id:
                self.sync_to_ebiz()

            templates = ebiz.client.service.GetEmailTemplates(**{
                'securityToken': ebiz._generate_security_json()
            })

            if templates:
                for template in templates:
                    odoo_temp = self.env['email.templates'].search([('template_id', '=', template['TemplateInternalId'])])
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

            wiz = self.env['wizard.ebiz.request.payment.method'].create({'partner_id':[[6,0,[self.id]]], 'email': self.email})
            action = self.env.ref('payment_ebizcharge.action_wizard_ebiz_request_payment_method').read()[0]
            action['res_id'] = wiz.id
            action['context'] = self.env.context
            return action

        except Exception as e:
            raise ValidationError(e)

    def read(self, fields):
        try:
            if len(self) == 1:
                # if self.request_payment_method_sent:
                self.with_context({'donot_sync': True}).ebiz_get_payment_methods()
        except Exception as e:
            _logger.exception(e)

        resp = super(ResPartner, self).read(fields)
        return resp

    def import_ebiz_customer(self):

        """
        Niaz Implementation:
        Getting All Ebiz Customers to Odoo Customers.

        Added button at random position(Customer Form), further on the position will be set according to PM instructions
        """

        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            get_all_customer = ebiz.client.service.SearchCustomers(**{
                'securityToken': ebiz._generate_security_json(),
                'start': 0,
                'limit': 1000000,
            })

            for customer in get_all_customer:
                odoo_customer = self.env['res.partner'].search([('ebiz_internal_id', '=', customer['CustomerInternalId']),
                                                                ('ebiz_customer_id','=', customer['CustomerId'])])
                if not odoo_customer:
                    customer_data = {}
                    complete_address = ''
                    if customer['LastName']:
                        customer_full_name = customer['FirstName'] + customer['LastName']
                    else:
                        customer_full_name = customer['FirstName']

                    if customer['ShippingAddress']['Address2']:
                        if customer['ShippingAddress']['Address1'] != customer['ShippingAddress']['Address2']:
                            complete_address = customer['ShippingAddress']['Address1'] + customer['ShippingAddress']['Address2']
                    else:
                        complete_address = customer['ShippingAddress']['Address1']

                    state_search = self.env['res.country.state'].search([('name', '=', customer['ShippingAddress']['State'])])
                    if state_search:
                        customer_data['state'] = state_search.id

                    country_search = self.env['res.country'].search([('name', '=', customer['ShippingAddress']['Country'])])
                    if country_search:
                        customer_data['Country'] = country_search.id

                    if customer_full_name:
                        customer_data = {
                            'name': customer_full_name,
                            'phone': customer['Phone'] if customer['Phone'] else '',
                            'mobile': customer['CellPhone'] if customer['CellPhone'] else '',
                            'ebiz_internal_id': customer['CustomerInternalId'],
                            'ebiz_customer_id': customer['CustomerId'],
                            'email': customer['Email'] if customer['Email'] else '',
                            'street': complete_address if complete_address else '',
                            'zip': customer['ShippingAddress']['ZipCode'] if customer['ShippingAddress']['ZipCode'] else '',
                            'city': customer['ShippingAddress']['City'] if customer['ShippingAddress']['City'] else '',
                            'customer_rank': 3,
                            'website': customer['WebSite'] if customer['WebSite'] else '',
                        }

                        self.env['res.partner'].create(customer_data)
                        self.env.cr.commit()

            return message_wizard('Customer imported successfully!')

        except Exception as e:
            raise UserError('Something Went Wrong!')

    def _ebiz_check_update_sync(self, values):
        """
        Kuldeeps implementation 
        def: checks if the after updating the customer should we run update sync base on the
        values that are updating.
        @params:
        values : update values params
        """
        update_fields = ["name", "company_name", "phone", "mobile", "email", "website",
        "street", "street2", "state_id", "zip", "city", "country_id","company_type", "parent_id"]
        for update_field in update_fields:
            if update_field in values:
                return True

        return False

    def request_payment_methods_bulk(self):

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

            # customer_ids = [ids.id for ids in self if ids.ebiz_internal_id]
            # if not customer_ids:
            #     raise UserError('The Selected Customers are not synced!')

            customer_ids = []
            self.env['email.recipients'].search([]).unlink()
            for customer in self:
                if customer.ebiz_internal_id:
                    recipient = self.env['email.recipients'].create({
                        'partner_id': customer.id,
                        'email': customer.email
                    })
                    customer_ids.append(recipient.id)
            return {'type': 'ir.actions.act_window',
                    'name': _('Request Payment Method'),
                    'res_model': 'wizard.ebiz.request.payment.method.bulk',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_partner_id': [[6, 0, customer_ids]],
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

    def js_flush_customer(self, *args, **kwargs):
        try:
            self.payment_token_ids.filtered(lambda x: x.create_uid == self.env.user).with_context({'donot_sync': True}).unlink()
        except MissingError as b:
            pass

    @api.model
    def cron_clean_payment_methods(self):
        acquirer = self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge')
        self.env['payment.token'].search([('acquirer_id','=',acquirer.id)]).unlink()

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super(ResPartner, self).search_read(domain, fields, offset, limit, order)
        # self.cron_clean_payment_methods()
        return res
