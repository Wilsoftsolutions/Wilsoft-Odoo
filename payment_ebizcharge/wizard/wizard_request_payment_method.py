
from odoo import models, api, fields
import json
from odoo.exceptions import UserError, ValidationError, Warning
from ..models.ebiz_charge import message_wizard


class RequestPaymentMethod(models.TransientModel):
    _name = 'wizard.ebiz.request.payment.method'

    partner_id = fields.Many2many('res.partner', string='Customer')

    def _default_template(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        templates = ebiz.client.service.GetEmailTemplates(**{
            'securityToken': ebiz._generate_security_json(),
        })
        self.env['email.templates'].search([]).unlink()

        if templates:
            for template in templates:
                self.env['email.templates'].create({
                    'name': template['TemplateName'],
                    'template_id': template['TemplateInternalId'],
                    'template_subject': template['TemplateSubject'],
                    'template_description': template['TemplateDescription'],
                    'template_type_id': template['TemplateTypeId'],
                })

        tem_check = self.env['email.templates'].search([('template_type_id', '=', 'AddPaymentMethodFormEmail')])
        if tem_check:
            return tem_check[0].id
        else:
            return None

    select_template = fields.Many2one('email.templates', string='Select Template', default=_default_template)
    # email_subject = fields.Char(string='Subject')
    email = fields.Char('Email')
    subject = fields.Char('Subject', related='select_template.template_subject', readonly=0)
    from_email = fields.Char( "From Email" )
    # payment_method_type = fields.Selection([('CC,ACH','Both'),('CC','Credit Card'),('ACH', "Bank Account")], 'Payment Method Type', default="CC")

    def get_default(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        get_allow_credit_card_pay = config.get('allow_credit_card_pay')

        if (get_merchant_data and get_allow_credit_card_pay) or get_allow_credit_card_pay:
            return 'CC'
        else:
            return 'ACH'

    payment_method_type = fields.Selection("check_ach_functionality", string='Payment Method Type', default=get_default)
    email_note = fields.Text('Additional Email Comments')

    def check_ach_functionality(self):
        """
        Gets Merchant transaction configuration
        """

        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        get_allow_credit_card_pay = config.get('allow_credit_card_pay')

        if get_merchant_data and get_allow_credit_card_pay:
            return [('CC,ACH', 'Both'), ('CC', 'Credit Card'), ('ACH', "Bank Account")]
        elif get_merchant_data:
            return [('ACH', "Bank Account")]
        elif get_allow_credit_card_pay:
            return [('CC', 'Credit Card')]
        else:
            return ''

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            partner = self.env['res.partner']
            addr = self.partner_id.address_get(['delivery', 'invoice'])
            ePaymentForm = {
                'FormType': 'PmRequestForm',
                'FromEmail': self.env.user.email,
                'FromName': self.env.user.name,
                'EmailSubject': self.subject,
                'EmailNotes': self.email_note if self.email_note else '',
                'EmailAddress': self.email,
                'EmailTemplateID': self.select_template.template_id,
                'EmailTemplateName': self.select_template.name,
                'CustFullName': self.partner_id.name,
                'BillingAddress': ebiz._get_customer_address(partner.browse(addr['invoice'])),
                'InvoiceNumber': 'PM',
                'PayByType': self.payment_method_type,
                'SoftwareId': 'Odoo CRM',
                'CustomerId': self.partner_id.id,
                'TotalAmount': 0.05,
                'AmountDue': 0.05,
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': True,
            }

            form_url = ebiz.client.service.GetEbizWebFormURL(**{
                'securityToken': ebiz._generate_security_json(),
                'ePaymentForm': ePaymentForm
            })
            self.partner_id.request_payment_method_sent = True
            return message_wizard('Payment method request was successfully sent.')

        except Exception as e:
            raise ValidationError(e)


class PaymentMethodBulk(models.TransientModel):
    _name = 'wizard.ebiz.request.payment.method.bulk'

    partner_id = fields.Many2many('email.recipients', string='Customer')

    def _default_template(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        templates = ebiz.client.service.GetEmailTemplates(**{
            'securityToken': ebiz._generate_security_json(),
        })
        self.env['email.templates'].search([]).unlink()

        if templates:
            for template in templates:
                self.env['email.templates'].create({
                    'name': template['TemplateName'],
                    'template_id': template['TemplateInternalId'],
                    'template_subject': template['TemplateSubject'],
                    'template_description': template['TemplateDescription'],
                    'template_type_id': template['TemplateTypeId'],
                })

        tem_check = self.env['email.templates'].search([('template_type_id', '=', 'AddPaymentMethodFormEmail')])
        if tem_check:
            return tem_check[0].id
        else:
            return None

    select_template = fields.Many2one('email.templates', string='Select Template', default=_default_template)
    # email_subject = fields.Char(string='Subject')
    # email = fields.Char('Email')
    subject = fields.Char('Subject', related='select_template.template_subject', readonly=0)
    # from_email = fields.Char( "From Email" )

    def get_default(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        get_allow_credit_card_pay = config.get('allow_credit_card_pay')

        if (get_merchant_data and get_allow_credit_card_pay) or get_allow_credit_card_pay:
            return 'CC'
        elif get_merchant_data:
            return 'ACH'
        else:
            return ''

    payment_method_type = fields.Selection("check_ach_functionality", string='Payment Method Type', default=get_default)
    email_note = fields.Text('Additional Email Comments')

    def check_ach_functionality(self):
        """
        Gets Merchant transaction configuration
        """

        config = self.env['res.config.settings'].sudo().default_get([])
        get_merchant_data = config.get('merchant_data')
        get_allow_credit_card_pay = config.get('allow_credit_card_pay')

        if get_merchant_data and get_allow_credit_card_pay:
            return [('CC,ACH', 'Both'), ('CC', 'Credit Card'), ('ACH', "Bank Account")]
        elif get_merchant_data:
            return [('ACH', "Bank Account")]
        elif get_allow_credit_card_pay:
            return [('CC', 'Credit Card')]
        else:
            return ''

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            resp_lines = []
            success = 0
            failed = 0
            total_count = len(self.partner_id)

            for record in self.partner_id:
                resp_line = {}
                resp_line['customer_name'] = resp_line['customer_id'] = record.partner_id.id
                resp_line['email_address'] = record.email

                if record.email and '@' in record.email and '.' in record.email:
                    ePaymentForm = {
                        'FormType': 'PmRequestForm',
                        'FromEmail': self.env.user.email,
                        'FromName': self.env.user.name,
                        'EmailSubject': self.subject,
                        'EmailNotes': self.email_note if self.email_note else '',
                        'EmailAddress': record.email,
                        'EmailTemplateID': self.select_template.template_id,
                        'EmailTemplateName': self.select_template.name,
                        'CustFullName': record.name,
                        # 'BillingAddress': ebiz._get_customer_address(partner.browse(addr['invoice'])),
                        'InvoiceNumber': 'PM',
                        'PayByType': self.payment_method_type,
                        'SoftwareId': 'Odoo CRM',
                        'CustomerId': record.partner_id.id,
                        'TotalAmount': 0.05,
                        'AmountDue': 0.05,
                        'ShowViewInvoiceLink': True,
                        'SendEmailToCustomer': True,
                    }

                    form_url = ebiz.client.service.GetEbizWebFormURL(**{
                        'securityToken': ebiz._generate_security_json(),
                        'ePaymentForm': ePaymentForm
                    })
                    record.partner_id.request_payment_method_sent = True
                    self.env['rpm.counter'].create({
                        'request_id': form_url.split('=')[1],
                        'counter': 1,
                    })

                    resp_line['status'] = 'Success'
                    success += 1
                    pending_requests = self.env['payment.method.ui'].search([])
                    if pending_requests:
                        for request in pending_requests:
                            # if request.transaction_history_line_pending:
                            counter = self.env['rpm.counter'].search([('request_id', '=', form_url.split('=')[1])])
                            line = {
                                "customer_name": int(record.partner_id.id),
                                "customer_id": str(record.partner_id.id),
                                "email_id": record.email,
                                "date_time": record.create_date,
                                "payment_internal_id": form_url.split('=')[1],
                                "sync_transaction_id_pending": request.id,
                                'no_of_times_sent': counter.counter if counter else 1,
                            }
                            new_pending_request = self.env['list.pending.payments.methods'].create(line)
                            request.transaction_history_line_pending = [[4, new_pending_request.id]]

                elif not record.email:
                    resp_line['status'] = 'Failed (No Email Address)'
                    failed += 1
                else:
                    resp_line['status'] = 'Failed (Wrong Email Address)'
                    failed += 1

                resp_lines.append([0, 0, resp_line])

            if self.env.context.get('active_model') == 'payment.method.ui':
                active_id = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))
                active_id.search_customers()

            wizard = self.env['wizard.multi.payment.message'].create({'name': 'send', 'lines_ids': resp_lines,
                                                                      'success_count': success, 'failed_count': failed,'total' : total_count })
            action = self.env.ref('payment_ebizcharge.wizard_multi_payment_message_action').read()[0]
            action['context'] = self._context
            action['res_id'] = wizard.id
            return action

        except Exception as e:
            raise ValidationError(e)


class EmailRecipients(models.TransientModel):
    _name = 'email.recipients'

    partner_id = fields.Many2one('res.partner',  string='Customer')
    email = fields.Char(string="Email")
    name = fields.Char(related='partner_id.name')

    def test_btn(self):
        self.email = True


class RPMCounter(models.Model):
    _name = 'rpm.counter'

    request_id = fields.Char(string='Request ID')
    counter = fields.Integer(string="Counter")
