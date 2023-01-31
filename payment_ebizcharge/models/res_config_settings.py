# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from .ebiz_charge import message_wizard


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    Choices = [('daily', 'Daily'),
               ('weekly', 'Weekly'),
               ('monthly', 'Monthly')]

    def _default_is_website_installed(self):
        web = self.env['ir.module.module'].sudo().search([('name','=','website_sale')])
        return True if web.state == "installed" else False

    def _default_is_website_ids(self):
        web = self.env['ir.module.module'].sudo().search([('name','=','website_sale')])
        default = []
        if web.state == "installed":
            webs = self.env['ebiz.website'].search([])
            return [[6, 0, webs.ids]]

    data_flushed = fields.Boolean('Data FLushed', defautl=False, config_parameter='payment_ebizcharge.data_flushed')
    ebiz_auto_sync_customer = fields.Boolean('Auto Sync Customers', defautl=False, config_parameter='payment_ebizcharge.ebiz_auto_sync_customer')
    ebiz_auto_sync_invoice = fields.Boolean('Auto Sync Invoices', defautl=False, config_parameter='payment_ebizcharge.ebiz_auto_sync_invoice')
    ebiz_auto_sync_sale_order = fields.Boolean('Auto Sync Sales Orders', defautl=False, config_parameter='payment_ebizcharge.ebiz_auto_sync_sale_order')
    ebiz_auto_sync_products = fields.Boolean('Auto Sync Products', defautl=False, config_parameter='payment_ebizcharge.ebiz_auto_sync_products')
    ebiz_auto_sync_credit_notes = fields.Boolean('Auto Sync Credit Notes', defautl=False, config_parameter='payment_ebizcharge.ebiz_auto_sync_credit_notes')
    ebiz_partial_payments = fields.Boolean('Enable partial payments')
    ebiz_auto_populate_amount = fields.Boolean('Auto populate payment amount fields with full balance')
    ebiz_default_pre_auth = fields.Boolean('Make "Pre-Auth" the default selection for payment type of estimates', config_parameter='payment_ebizcharge.ebiz_default_pre_auth')
    ebiz_email_payment_receipt = fields.Boolean('Send email receipt to customer')
    ebiz_email_pay_for_invoice = fields.Boolean('Send email receipt to customer')
    ebiz_email_pay_for_sale_order = fields.Boolean('Send email receipt to customer')
    ebiz_enable_sub_customer = fields.Boolean('Enable Sub Customers')
    ebiz_sync_bundle_item = fields.Boolean('Sync Bundle Line Items')
    ebiz_order_transaction_commands = fields.Selection([
        ('pre-auth-and-deposit', 'Allow pre-auth and deposits taken on orders'),
        ('pre-auth', 'Allow only pre-auth on order'),
        ('deposit', 'Allow only deposits on the order')], 'Payments on order',
        default='pre-auth-and-deposit', config_parameter='payment_ebizcharge.ebiz_order_transaction_commands')
    ebiz_invoice_transaction_commands = fields.Selection([
        ('pre-auth-and-deposit', 'Allow pre-auth and deposits taken on invoices'),
        ('pre-auth', 'Allow only pre-auth on invoices'),
        ('deposit', 'Allow only deposits on invoices')], 'Payments on Invoice',
        default='pre-auth-and-deposit', config_parameter='payment_ebizcharge.ebiz_invoice_transaction_commands')
    ebiz_security_key = fields.Char('Security key', config_parameter='payment_ebizcharge.ebiz_security_key')
    ebiz_user_id = fields.Char('User ID', config_parameter='payment_ebizcharge.ebiz_user_id')
    ebiz_password = fields.Char('Password', config_parameter='payment_ebizcharge.ebiz_password')

    auto_sync = fields.Boolean('Auto Scheduler', default=False, config_parameter='payment_ebizcharge.auto_sync')
    next_execution_date = fields.Datetime(string='Next Execution Date')
    interval_number = fields.Integer(string="Execute Every", config_parameter='payment_ebizcharge.interval_number')
    interval_unit = fields.Selection(string="Interval", selection=[
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'), ], config_parameter='payment_ebizcharge.interval_unit')

    next_execution_date_invoice = fields.Datetime(string='Next Execution Date')
    interval_number_invoice = fields.Integer(string="Interval", config_parameter='payment_ebizcharge.interval_number_invoice')
    interval_unit_invoice = fields.Selection(string="Frequency", selection=[
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),], config_parameter='payment_ebizcharge.interval_unit_invoice')

    ebiz_website_allowed_command = fields.Selection([
        ('pre-auth', 'Allow authorization only'),
        ('deposit', 'Allow authorization and capture')],
        string = 'eCommerce Orders', default='pre-auth',
        config_parameter='payment_ebizcharge.ebiz_website_allowed_command')

    time_spam_test = fields.Datetime(string='Next Execution Date')
    time_spam_test_product = fields.Datetime(string='Next Execution Date Product')
    time_spam_test_invoices = fields.Datetime(string='Next Execution Date Invoices')
    time_spam_test_sale_order = fields.Datetime(string='Next Execution Date SaleOrder')

    ebiz_document_download_range = fields.Selection([
        ('1-week', 'One Week'),
        ('2-week', 'Two Weeks'),
        ('1-month', 'One Month'),
        ('2-month', 'Two Months'),
        ('6-month', 'Six Months'),
        ('1-year', 'One Year')], 'Document Download Date Range', required=True,
        default='1-week', config_parameter='payment_ebizcharge.ebiz_document_download_range')

    is_website_installed = fields.Boolean(default=_default_is_website_installed)

    def _compute_is_website_installed(self):
        web = self.env['ir.module.module'].sudo().search([('name','=','website_sale')])
        for se in self:
            se.is_website_installed = True if web else False

    def get_timezone(self):
        self.time_zone = self.env.user.tz

    time_zone = fields.Char('Time Zone', readonly=1,  default='get_timezone')

    @api.model
    def _compute_schedular_auto_check(self):
        schedular = self.env['ir.cron'].search([('name', '=', 'Received Payments (Invoice)')])
        set = self.env['ir.config_parameter'].set_param('payment_ebizcharge.scheduler_act_deact', schedular.active if schedular else False)
        get = self.env['ir.config_parameter'].get_param('payment_ebizcharge.scheduler_act_deact')
        self.scheduler_act_deact = set

    scheduler_act_deact = fields.Boolean(string='Scheduler Check', default=False)

    invoice_cron_job = fields.Boolean('Download and apply payments', default=False, config_parameter='payment_ebizcharge.invoice_cron_job')
    sale_cron_job = fields.Boolean('Receive Quotation/SaleOrder Email Payments', default=False, config_parameter='payment_ebizcharge.sale_cron_job')

    website = fields.Reference(selection='_select_target_model', string="Select Website")
    # ebiz_website_id = fields.Many2one('ebiz.website', string="Website", ondelete='cascade')
    # ebiz_website_ids = fields.One2many('ebiz.website', 'res_config_id', default=_default_is_website_ids)
    # ebiz_website_security_token = fields.Char('Security Key', related='ebiz_website_id.ebiz_security_key')

    ebiz_security_key_web = fields.Char('Security key', readonly=0, related="website_id.ebiz_security_key")
    ebiz_user_id_web = fields.Char('User ID', readonly=0, related="website_id.ebiz_user_id")
    ebiz_password_web = fields.Char('Password', readonly=0, related="website_id.ebiz_password")
    ebiz_default_web = fields.Boolean('Set as Default', readonly=0, related="website_id.ebiz_default")
    ebiz_add_New = fields.Boolean(readonly=0, related="website_id.ebiz_add_New")
    ebiz_use_defaults = fields.Boolean(readonly=0, related="website_id.ebiz_use_defaults")
    """Delete ebiz_use_default as soon as possible"""
    # ebiz_use_default = fields.Selection([('default', 'Default'), ('new', 'Add New')], 'Use Default')
    ebiz_settings_way = fields.Selection([('default', 'Default'), ('new', 'Add New')], 'Use Default')

    ebiz_security_key_web_def = fields.Char('Security Key', config_parameter='payment_ebizcharge.ebiz_security_key_web_def')
    ebiz_user_id_web_def = fields.Char('User ID', config_parameter='payment_ebizcharge.ebiz_user_id_web_def')
    ebiz_password_web_def = fields.Char('Password', config_parameter='payment_ebizcharge.ebiz_password_web_def')

    merchant_data = fields.Boolean('Merchant Data', config_parameter='payment_ebizcharge.merchant_data')
    merchant_card_verification = fields.Char('Merchant Data', config_parameter='payment_ebizcharge.merchant_card_verification')
    verify_card_before_saving = fields.Boolean('Verify Card Before Saving', config_parameter='payment_ebizcharge.verify_card_before_saving')
    use_full_amount_for_avs = fields.Char('UseFullAmountForAVS', config_parameter='payment_ebizcharge.use_full_amount_for_avs')
    allow_credit_card_pay = fields.Boolean('AllowCreditCardPayments', config_parameter='payment_ebizcharge.allow_credit_card_pay')
    enable_cvv = fields.Boolean('EnableCVV', config_parameter='payment_ebizcharge.enable_cvv')

    @api.onchange('ebiz_use_defaults')
    def onUseDefaultChange(self):
        for i in self:
            if i.ebiz_use_defaults:
                i.ebiz_add_New = False

    @api.onchange('ebiz_add_New')
    def onAddNewChange(self):
        for i in self:
            if i.ebiz_add_New:
                i.ebiz_use_defaults = False

    @api.onchange('ebiz_default_web')
    def onDefaultChange(self):
        for i in self:
            if i.ebiz_default_web:
                websites = self.env['website'].search([('id', '!=', i.website_id.id)])
                for website in websites:
                    website.ebiz_default = False

    @api.model
    def _select_target_model(self):
        models = self.env['ir.model'].search([('model', '=', 'website')])
        return [(model.model, model.name) for model in models]

    @api.model
    def default_get(self, fields):
        res = super(ResConfigSettings, self).default_get(fields)
        res['time_zone'] = self.env.user.tz
        return res

    def get_document_download_start_date(self):
        config = self.default_get([])
        return self.get_start_date(*config.get('ebiz_document_download_range').split('-'))

    def get_start_date(self, step=1, step_type='week'):
        step_type = step_type if step_type[-1] == 's' else step_type + 's'
        end = datetime.now()
        start = end - relativedelta(**{step_type:int(step)})
        return start.date()

    def activate_invoice_cron_job(self):
        done = False
        while not done:
            try:
                scheduler = self.env.ref('payment_ebizcharge.received_payments')

                if scheduler and self.invoice_cron_job:
                    scheduler.active = True
                    scheduler.nextcall = self.next_execution_date_invoice if self.next_execution_date_invoice else datetime.now()
                    scheduler.interval_number = self.interval_number_invoice
                    scheduler.interval_type = self.interval_unit_invoice
                    self.env['ir.config_parameter'].set_param('payment_ebizcharge.scheduler_act_deact', True)
                    self.env['ir.config_parameter'].set_param('payment_ebizcharge.time_zone', self.env.user.tz)
                    # self.scheduler_act_deact = True

                self.env.cr.commit()
                done = True
            except Exception as e:
                raise ValidationError(str(e))

        else:
            return message_wizard('Scheduler Activated!')
            
    def deactivate_invoice_cron_job(self):
        done = False
        while not done:
            try:
                scheduler = self.env.ref('payment_ebizcharge.received_payments')

                if scheduler and self.invoice_cron_job:
                    scheduler.active = False
                    self.env['ir.config_parameter'].set_param('payment_ebizcharge.scheduler_act_deact', False)
                    self.env['ir.config_parameter'].set_param('payment_ebizcharge.time_zone', self.env.user.tz)

                    # self.scheduler_act_deact = False

                self.env.cr.commit()
                done = True
            except Exception as e:
                raise ValidationError(str(e))

        else:
            return message_wizard('Scheduler Deactivated!')

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        if self.next_execution_date or self.next_execution_date_invoice:
            param.set_param('payment_ebizcharge.next_execution_date', self.next_execution_date)
            param.set_param('payment_ebizcharge.next_execution_date_invoice', self.next_execution_date_invoice)
            # param.set_param('payment_ebizcharge.active_deactive', self.active_deactive)
            return param
        else:
            return param

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        val = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.next_execution_date')
        val2 = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.next_execution_date_invoice')
        val3 = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.scheduler_act_deact')
        val4 = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.time_zone')
        # val1 = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.active_deactive')
        res.update(next_execution_date=val, next_execution_date_invoice=val2, scheduler_act_deact=True if val3=='True' else False, time_zone=val4)

        if self.ebiz_security_key_web and self.ebiz_user_id_web and self.ebiz_password_web:
            web = self.env['website'].search([('id', '=', self.website_id.id)])
            if web:
                web.ebiz_security_key = self.ebiz_security_key_web
                web.ebiz_user_id = self.ebiz_user_id_web
                web.ebiz_password = self.ebiz_password_web
        return res

    def view_scheduled_actions(self):
        return {
            'name': (_('Automated Actions')),
            'view_type': 'form',
            'res_model': 'ir.cron',
            'target': 'new',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }


class WebsiteSettings(models.Model):
    _inherit = 'website'

    ebiz_security_key = fields.Char('Security key')
    ebiz_user_id = fields.Char('User ID')
    ebiz_password = fields.Char('Password')
    ebiz_default = fields.Boolean('Default Setting')
    ebiz_add_New = fields.Boolean(default=False)
    ebiz_use_defaults = fields.Boolean(default=True)
    # ebiz_use_default = fields.Selection([('default', 'Default'), ('new', 'Add New')], 'Use Default')
    ebiz_settings_way = fields.Selection([('default', 'Default'), ('new', 'Add New')], 'Use Default')

    merchant_data = fields.Boolean('Merchant Data')
    merchant_card_verification = fields.Char('Merchant Data')
    verify_card_before_saving = fields.Boolean('Verify Card Before Saving')
    allow_credit_card_pay = fields.Boolean('AllowCreditCardPayments')
    enable_cvv = fields.Boolean('EnableCVV')

    @api.model
    def create(self, values):
        # print(values)
        return super(WebsiteSettings, self).create(values)

    def write(self, values):
        # print(values)
        return super(WebsiteSettings, self).write(values)


class WebsiteMiddleware(models.TransientModel):
    _name = 'ebiz.website'

    website_id = fields.Integer('website_id')
    res_config_id = fields.Many2one('res.config.settings')
    name = fields.Char('Name')
    ebiz_security_key = fields.Char('Security Key')
    ebiz_username = fields.Char('User ID')
    ebiz_password = fields.Char('Password')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        web = self.env['ir.module.module'].sudo().search([('name','=','website_sale')])
        if web.state == "installed":
            all_web = self.env['website'].search([])
            all_existing = [ w['website_id'] for w in self.search([]).read(['website_id'])]

            for web in all_web:
                if web.id not in all_existing:
                    create_params = {
                        'website_id': web.id,
                        'name': web.name,
                    }
                    ebiz_web = self.env['ebiz.website.config'].search(['website_id','=',web.id])
                    if ebiz_web.ebiz_security_key:
                        create_params['ebiz_security_key'] = ebiz_web.ebiz_security_key
                    if ebiz_web.ebiz_username:
                        create_params['ebiz_username'] = ebiz_web.ebiz_username
                    if ebiz_web.ebiz_password:
                        create_params['ebiz_password'] = ebiz_web.ebiz_password
                    self.create(create_params)
        return super(WebsiteMiddleware, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        web = self.env['ir.module.module'].sudo().search([('name','=','website_sale')])
        if web.state == "installed":
            all_web = self.env['website'].search([])
            all_existing = [ w['website_id'] for w in self.search([]).read(['website_id'])]

            for web in all_web:
                if web.id not in all_existing:
                    create_params = {
                        'website_id': web.id,
                        'name': web.name,
                    }
                    ebiz_web = self.env['ebiz.website.config'].search([('website_id','=',web.id)])
                    if ebiz_web.ebiz_security_key:
                        create_params['ebiz_security_key'] = ebiz_web.ebiz_security_key
                    if ebiz_web.ebiz_username:
                        create_params['ebiz_username'] = ebiz_web.ebiz_username
                    if ebiz_web.ebiz_password:
                        create_params['ebiz_password'] = ebiz_web.ebiz_password
                    self.create(create_params)
        return super(WebsiteMiddleware, self).name_search(domain, fields, offset, limit, order)

    def write(self, values):
        res = super(WebsiteMiddleware, self).write(values)
        for web in self:
            params = {
                        'name': web.name,
                    }
            if web.ebiz_security_key:
                params['ebiz_security_key'] = web.ebiz_security_key
            if web.ebiz_username:
                params['ebiz_username'] = web.ebiz_username
            if web.ebiz_password:
                params['ebiz_password'] = web.ebiz_password

            ebiz_web = self.env['ebiz.website.config'].search([('website_id','=',web.website_id)])
            if ebiz_web:
                ebiz_web.write(params)
            else:
                params['website_id'] = web.website_id
                self.env['ebiz.website.config'].create(params)
        return res


class EbizWebsiteSecurity(models.Model):
    _name = 'ebiz.website.config'

    website_id = fields.Integer('website_id')
    name = fields.Char('Name')
    ebiz_security_key = fields.Char('Security key')
    ebiz_username = fields.Char('Security key')
    ebiz_password = fields.Char('Security key')
