
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime
from zeep import Client
from ..models.ebiz_charge import message_wizard


class EmailInvoice(models.TransientModel):

    _name = 'email.invoice'

    contacts_to = fields.Many2many('res.partner', string='Customer')

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

        tem_check = self.env['email.templates'].search([('template_type_id', '=', 'WebFormEmail')])
        if tem_check:
            return tem_check[0].id
        else:
            return None

    select_template = fields.Many2one('email.templates', string='Select Template', default=_default_template)
    email_subject = fields.Char(string='Subject', related='select_template.template_subject', readonly=0)
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('')
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)

    def _transaction_line(self, line):
        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        tax_ids = line.tax_ids if hasattr(line, 'tax_ids') else line.tax_id
        price_tax = line.price_tax if hasattr(line, 'price_tax') else 0
        return {
            'SKU': line.product_id.id,
            'ProductName': line.product_id.name,
            'Description': line.name,
            'UnitPrice': line.price_unit,
            'Taxable': True if tax_ids else False,
            'TaxAmount': int(price_tax),
            'Qty': int(qty),
        }

    def _transaction_lines(self, lines):
        item_list = []
        for line in lines:
            item_list.append(self._transaction_line(line))
        return {'TransactionLineItem': item_list}

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            saleorder = self.env['account.move'].search([('id', '=', self.record_id)])
            if self.env.context.get('active_model') == 'sale.order':
                if saleorder.invoice_ids:
                    if saleorder.invoice_ids.amount_residual < self.amount:
                        raise UserError('Amount cannot be greater than amount due!')
                else:
                    if saleorder.amount_total < self.amount:
                        raise UserError('Amount cannot be greater than amount due!')
            else:
                if saleorder.amount_residual < self.amount:
                    raise UserError('Amount cannot be greater than amount due!')

            if not '@' in self.email_customer or not '.' in self.email_customer:
                raise UserError('You might have entered the wrong Email Address!')

            # if not saleorder.partner_id.email:
            #     raise UserError(f'"{saleorder.partner_id.name}" does not contain Email Address!')

            fname = saleorder.partner_id.name.split(' ')
            lname = ''
            for name in range(1, len(fname)):
                lname += fname[name]

            address = ''
            if saleorder.partner_id.street:
                address += saleorder.partner_id.street
            if saleorder.partner_id.street2:
                address += ' ' + saleorder.partner_id.street2

            try:
                lines = saleorder.order_line
            except AttributeError:
                lines = saleorder.invoice_line_ids

            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': self.env.user.email,
                'FromName': self.env.user.name,
                'EmailSubject': self.email_subject,
                # 'EmailAddress': saleorder.partner_id.email,
                'EmailAddress': self.email_customer,
                'EmailTemplateID': self.select_template.template_id,
                'EmailTemplateName': self.select_template.name,
                # 'SavePaymentMethod': True,
                'ShowSavedPaymentMethods': True,
                'CustFullName': saleorder.partner_id.name,
                # 'EmailNotes': 'test Note',
                'TotalAmount': saleorder.amount_total,
                'AmountDue': self.amount,
                # 'ShippingAmount': self.amount,
                # 'Description': 'test description',
                'CustomerId':  saleorder.partner_id.ebiz_customer_id or saleorder.partner_id.id,
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': True,
                'TaxAmount': saleorder.amount_tax,
                'SoftwareId': 'Odoo CRM',
                'DocumentTypeId': 'Invoice',
                # 'CurrencyCode': self.env.ref('base.main_company').currency_id.name,
                # 'Date': saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else '',
                'InvoiceNumber': str(saleorder.id) if str(saleorder.name) == '/' else str(saleorder.name),
                'BillingAddress': {
                                    "FirstName": fname[0],
                                    "LastName": lname,
                                    "CompanyName": saleorder.partner_id.company_name if saleorder.partner_id.company_name else '',
                                    "Address1": address,
                                    # "Address2": saleorder.partner_id.street2,
                                    "City": saleorder.partner_id.city if saleorder.partner_id.city else '',
                                    "State": saleorder.partner_id.state_id.code or 'CA',
                                    "ZipCode": saleorder.partner_id.zip or '',
                                    "Country": saleorder.partner_id.country_id.code or 'US',
                                },
                "LineItems": self._transaction_lines(lines),
            }
            if saleorder.partner_id.ebiz_customer_id:
                ePaymentForm['CustomerId'] = saleorder.partner_id.ebiz_customer_id

            if self.env.context.get('active_model') == 'sale.order':
                ePaymentForm['Date'] = saleorder.date_order.date()
                ePaymentForm['SalesOrderInternalId'] = saleorder.ebiz_internal_id
                ePaymentForm['Description'] = 'SaleOrder'
            else:
                ePaymentForm['Date'] = saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else ''
                ePaymentForm['InvoiceInternalId'] = saleorder.ebiz_internal_id
                ePaymentForm['Description'] = 'Invoice'
                
            form_url = ebiz.client.service.GetEbizWebFormURL(**{
                'securityToken': ebiz._generate_security_json(),
                'ePaymentForm': ePaymentForm
            })

            if self.env.context.get('active_model') == 'sale.order':
                saleorder.action_confirm()
                saleorder.write({
                    # 'state': 'done',
                    'ebiz_invoice_status': 'pending',
                    'payment_internal_id': form_url.split('=')[1],
                })
            else:
                saleorder.write({
                    'payment_internal_id': form_url.split('=')[1],
                    'ebiz_invoice_status': 'pending',
                    'date_time_sent_for_email': datetime.now(),
                    'email_for_pending': self.email_customer,
                    'email_recieved_payments': False,
                    'email_requested_amount': self.amount,
                    'save_payment_link': form_url,
                    'no_of_times_sent': 1,
                })

            return message_wizard('Email pay request has been sent successfully!')

        except Exception as e:
            raise ValidationError(e)


class EmailInvoiceMultiple(models.TransientModel):
    _name = 'multiple.email.invoice'

    contacts_to = fields.Many2many('res.partner', string='Customer')
    invoicess_to = fields.Many2many('account.move', string='Invoice')
    select_template = fields.Many2one('email.templates', string='Select Template')
    email_subject = fields.Char(string='Subject')
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('', related='contacts_to.email', readonly=True)
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)

    def _transaction_line(self, line):
        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        tax_ids = line.tax_ids if hasattr(line, 'tax_ids') else line.tax_id
        price_tax = line.price_tax if hasattr(line, 'price_tax') else 0
        return {
            'SKU': line.product_id.id,
            'ProductName': line.product_id.name,
            'Description': line.name,
            'UnitPrice': line.price_unit,
            'Taxable': True if tax_ids else False,
            'TaxAmount': int(price_tax),
            'Qty': int(qty),
        }

    def _transaction_lines(self, lines):
        item_list = []
        for line in lines:
            item_list.append(self._transaction_line(line))
        return {'TransactionLineItem': item_list}

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

            if not saleorder.partner_id.email:
                raise UserError(f'"{saleorder.partner_id.name}" does not contain Email Address!')

            fname = saleorder.partner_id.name.split(' ')
            lname = ''
            for name in range(1, len(fname)):
                lname += fname[name]

            address = ''
            if saleorder.partner_id.street:
                address += saleorder.partner_id.street
            if saleorder.partner_id.street2:
                address += ' ' + saleorder.partner_id.street2

            try:
                lines = saleorder.order_line
            except AttributeError:
                lines = saleorder.invoice_line_ids

            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': self.env.user.email,
                'FromName': self.env.user.name,
                'EmailSubject': self.select_template.template_subject,
                'EmailAddress': saleorder.partner_id.email,
                'EmailTemplateID': self.select_template.template_id,
                'EmailTemplateName': self.select_template.name,
                # 'SavePaymentMethod': True,
                'ShowSavedPaymentMethods': True,
                'CustFullName': saleorder.partner_id.name,
                # 'EmailNotes': 'test Note',
                # 'TotalAmount': saleorder.amount_total,
                'TotalAmount': saleorder.amount_total,
                'AmountDue': self.amount,
                # 'ShippingAmount': self.amount,
                # 'Description': 'test description',
                'CustomerId':  saleorder.partner_id.ebiz_customer_id,
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': True,
                'TaxAmount': saleorder.amount_tax,
                # 'CurrencyCode': self.env.ref('base.main_company').currency_id.name,
                # 'Date': saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else '',
                'InvoiceNumber': str(saleorder.id),
                'BillingAddress': {
                                    "FirstName": fname[0],
                                    "LastName": lname,
                                    "CompanyName": saleorder.partner_id.company_name if saleorder.partner_id.company_name else '',
                                    "Address1": address,
                                    # "Address2": saleorder.partner_id.street2,
                                    "City": saleorder.partner_id.city if saleorder.partner_id.city else '',
                                    "State": saleorder.partner_id.state_id.code if saleorder.partner_id.state_id.code else 'CA',
                                    "ZipCode": saleorder.partner_id.zip if saleorder.partner_id.zip else '',
                                    "Country": saleorder.partner_id.country_id.code if saleorder.partner_id.country_id.code else 'US',
                                },
                "LineItems": self._transaction_lines(lines),
            }

            if saleorder.partner_id.ebiz_customer_id:
                ePaymentForm['CustomerId'] = saleorder.partner_id.ebiz_customer_id

            if self.env.context.get('active_model') == 'sale.order':
                ePaymentForm['Date'] = saleorder.date_order.date()
            else:
                ePaymentForm['Date'] = saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else ''

            form_url = ebiz.client.service.GetEbizWebFormURL(**{
                'securityToken': ebiz._generate_security_json(),
                'ePaymentForm': ePaymentForm
            })

            if self.env.context.get('active_model') == 'sale.order':
                saleorder.action_confirm()
                saleorder.write({
                    # 'state': 'done',
                    'ebiz_invoice_status': 'pending',
                    'payment_internal_id': form_url.split('=')[1],
                })
            else:
                saleorder.write({
                    'payment_internal_id': form_url.split('=')[1],
                    'ebiz_invoice_status': 'pending',
                })

            return message_wizard('Email has been sent successfully!')

        except Exception as e:
            raise ValidationError(e)


class EmailInvoiceMultiplePayments(models.TransientModel):
    _name = 'multiple.email.invoice.payments'

    contacts_to = fields.Many2many('res.partner', string='Customer')
    invoicess_to = fields.Many2many('account.move', string='Invoice')
    select_template = fields.Many2one('email.templates', string='Select Template')
    email_subject = fields.Char(string='Subject')
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('', related='contacts_to.email', readonly=True)
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)

    def _transaction_line(self, line):
        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        tax_ids = line.tax_ids if hasattr(line, 'tax_ids') else line.tax_id
        price_tax = line.price_tax if hasattr(line, 'price_tax') else 0
        return {
            'SKU': line.product_id.id,
            'ProductName': line.product_id.name,
            'Description': line.name,
            'UnitPrice': line.price_unit,
            'Taxable': True if tax_ids else False,
            'TaxAmount': int(price_tax),
            'Qty': int(qty),
        }

    def _transaction_lines(self, lines):
        item_list = []
        for line in lines:
            item_list.append(self._transaction_line(line))
        return {'TransactionLineItem': item_list}

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

            if not saleorder.partner_id.email:
                raise UserError(f'"{saleorder.partner_id.name}" does not contain Email Address!')

            fname = saleorder.partner_id.name.split(' ')
            lname = ''
            for name in range(1, len(fname)):
                lname += fname[name]

            address = ''
            if saleorder.partner_id.street:
                address += saleorder.partner_id.street
            if saleorder.partner_id.street2:
                address += ' ' + saleorder.partner_id.street2

            try:
                lines = saleorder.order_line
            except AttributeError:
                lines = saleorder.invoice_line_ids

            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': self.env.user.email,
                'FromName': self.env.user.name,
                'EmailSubject': self.select_template.template_subject,
                'EmailAddress': saleorder.partner_id.email,
                'EmailTemplateID': self.select_template.template_id,
                'EmailTemplateName': self.select_template.name,
                # 'SavePaymentMethod': True,
                'ShowSavedPaymentMethods': True,
                'CustFullName': saleorder.partner_id.name,
                # 'EmailNotes': 'test Note',
                # 'TotalAmount': saleorder.amount_total,
                'TotalAmount': saleorder.amount_total,
                'AmountDue': self.amount,
                # 'ShippingAmount': self.amount,
                # 'Description': 'test description',
                'CustomerId':  saleorder.partner_id.ebiz_customer_id,
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': True,
                'TaxAmount': saleorder.amount_tax,
                # 'CurrencyCode': self.env.ref('base.main_company').currency_id.name,
                # 'Date': saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else '',
                'InvoiceNumber': str(saleorder.id),
                'BillingAddress': {
                                    "FirstName": fname[0],
                                    "LastName": lname,
                                    "CompanyName": saleorder.partner_id.company_name if saleorder.partner_id.company_name else '',
                                    "Address1": address,
                                    # "Address2": saleorder.partner_id.street2,
                                    "City": saleorder.partner_id.city if saleorder.partner_id.city else '',
                                    "State": saleorder.partner_id.state_id.code if saleorder.partner_id.state_id.code else 'CA',
                                    "ZipCode": saleorder.partner_id.zip if saleorder.partner_id.zip else '',
                                    "Country": saleorder.partner_id.country_id.code if saleorder.partner_id.country_id.code else 'US',
                                },
                "LineItems": self._transaction_lines(lines),
            }

            if saleorder.partner_id.ebiz_customer_id:
                ePaymentForm['CustomerId'] = saleorder.partner_id.ebiz_customer_id

            if self.env.context.get('active_model') == 'sale.order':
                ePaymentForm['Date'] = saleorder.date_order.date()
            else:
                ePaymentForm['Date'] = saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else ''

            form_url = ebiz.client.service.GetEbizWebFormURL(**{
                'securityToken': ebiz._generate_security_json(),
                'ePaymentForm': ePaymentForm
            })

            if self.env.context.get('active_model') == 'sale.order':
                saleorder.action_confirm()
                saleorder.write({
                    # 'state': 'done',
                    'ebiz_invoice_status': 'pending',
                    'payment_internal_id': form_url.split('=')[1],
                })
            else:
                saleorder.write({
                    'payment_internal_id': form_url.split('=')[1],
                    'ebiz_invoice_status': 'pending',
                })

            return message_wizard('Email has been sent successfully!')

        except Exception as e:
            raise ValidationError(e)
