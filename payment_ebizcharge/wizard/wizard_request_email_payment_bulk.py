from odoo import fields, models,api, _
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError, Warning
from zeep import Client


class EmailPyamentWizard(models.TransientModel):
    _name = 'ebiz.request.payment.bulk'

    payment_lines = fields.One2many('ebiz.payment.lines.bulk', 'wizard_id')

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

    def send_email(self):
        try:
            resp_lines = []
            success = 0
            failed = 0
            total_count = len(self.payment_lines)

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            if not self.payment_lines:
                raise UserError('Please select a record first!')

            for record in self.payment_lines:
                saleorder = self.env['account.move'].search([('id', '=', record.invoice_id)])

                resp_line = {}
                resp_line['customer_name'] = resp_line['customer_id'] = record.customer_name.id
                resp_line['number'] = record.invoice_id

                if record.email_id and '@' in record.email_id and '.' in record.email_id:
                    if saleorder.state != 'posted':
                        saleorder.action_post()

                    if not saleorder.ebiz_internal_id:
                        saleorder.sync_to_ebiz()

                    # saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

                    if saleorder.amount_residual < record.amount_due:
                        raise UserError('Amount cannot be greater than amount due!')

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
                        'EmailAddress': record.email_id,
                        'EmailTemplateID': self.select_template.template_id,
                        'EmailTemplateName': self.select_template.name,
                        # 'SavePaymentMethod': True,
                        'ShowSavedPaymentMethods': True,
                        'CustFullName': saleorder.partner_id.name,
                        # 'EmailNotes': 'test Note',
                        'TotalAmount': saleorder.amount_total,
                        'AmountDue': record.amount_due,
                        'DocumentTypeId': 'Invoice',
                        'ShippingAmount': record.amount_due,
                        # 'Description': 'test description',
                        'CustomerId': saleorder.partner_id.id,
                        'ShowViewInvoiceLink': True,
                        'SendEmailToCustomer': True,
                        'TaxAmount': saleorder.amount_tax,
                        'SoftwareId': 'Odoo CRM',
                        # 'CurrencyCode': self.env.ref('base.main_company').currency_id.name,
                        'Date': str(saleorder.invoice_date) if saleorder.invoice_date else '',
                        'InvoiceNumber': str(saleorder.id) if str(saleorder.name) == '/' else str(saleorder.name),
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


                    ePaymentForm[
                        'Date'] = saleorder.invoice_date if saleorder.invoice_date else saleorder.invoice_date_due if saleorder.invoice_date_due else ''
                    ePaymentForm['InvoiceInternalId'] = saleorder.ebiz_internal_id
                    ePaymentForm['Description'] = 'Invoice'

                    form_url = ebiz.client.service.GetEbizWebFormURL(**{
                        'securityToken': ebiz._generate_security_json(),
                        'ePaymentForm': ePaymentForm
                    })

                    saleorder.write({
                        'payment_internal_id': form_url.split('=')[1],
                        'ebiz_invoice_status': 'pending',
                        'date_time_sent_for_email': datetime.now(),
                        'email_for_pending': record.email_id,
                        'email_requested_amount': record.amount_due,
                        'email_recieved_payments': False,
                        'save_payment_link': form_url,
                        'no_of_times_sent': 1,
                    })

                    resp_line['status'] = 'Success'
                    success += 1
                    emailInvoices = self.env['payment.request.bulk.email'].search([])
                    if emailInvoices:
                        list_of_pending = []
                        partner = record.customer_name
                        odooInvoice = self.env['account.move'].search([('id', '=', int(record.invoice_id))])
                        date_check = False
                        if odooInvoice.date_time_sent_for_email:
                            date_check = 'due in 3 days' if (datetime.now() - odooInvoice.date_time_sent_for_email).days <= 3 \
                                else '3 days overdue'
                        dict2 = (0, 0, {
                            'name': record['name'],
                            'customer_name': partner.id,
                            'customer_id': partner.id,
                            'invoice_id': record.invoice_id,
                            'invoice_date': odooInvoice.date,
                            'email_id': record.email_id if record.email_id else partner.email,
                            'sales_person': self.env.user.id,
                            'amount': odooInvoice.amount_total,
                            "currency_id": record.currency_id.id,
                            'amount_due': odooInvoice.amount_residual_signed,
                            'tax': odooInvoice.amount_untaxed_signed,
                            'date_and_time_Sent': odooInvoice.date_time_sent_for_email or None,
                            'over_due_status': date_check if date_check else None,
                            'invoice_due_date': odooInvoice.invoice_date_due,
                            'sync_transaction_id_pending': self.id,
                            'ebiz_status': 'Pending' if odooInvoice.ebiz_invoice_status == 'pending' else odooInvoice.ebiz_invoice_status,
                            'email_requested_amount': odooInvoice.email_requested_amount,
                            'no_of_times_sent': odooInvoice.no_of_times_sent,
                        })
                        list_of_pending.append(dict2)
                        for emailInvoice in emailInvoices:
                            if emailInvoice.transaction_history_line:
                                for line in emailInvoice.transaction_history_line:
                                    if line.invoice_id == record.invoice_id:
                                        emailInvoice.transaction_history_line = [[2, line.id]]
                            emailInvoice.write({
                                'transaction_history_line_pending': list_of_pending
                            })

                elif not record.email_id:
                    resp_line['status'] = 'Failed (No Email Address)'
                    failed += 1
                else:
                    resp_line['status'] = 'Failed (Wrong Email Address)'
                    failed += 1

                resp_lines.append([0, 0, resp_line])

            else:
                # id_reload = self.env[('payment.request.bulk.email')].browse(self.env.context.get('active_id'))
                # if id_reload:
                #     id_reload.search_transaction()

                wizard = self.env['wizard.email.pay.message'].create({'name': 'email_pay', 'lines_ids': resp_lines,
                                                                          'success_count': success,
                                                                          'failed_count': failed,
                                                                          'total': total_count})

                return {'type': 'ir.actions.act_window',
                        'name': _('Email Pay for Invoices'),
                        'res_model': 'wizard.email.pay.message',
                        'target': 'new',
                        'res_id': wizard.id,
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'context':
                            self._context,
                        }

        except Exception as e:
            raise ValidationError(e)



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


class EbizPaymentLines(models.TransientModel):
    _name = 'ebiz.payment.lines.bulk'

    wizard_id = fields.Many2one('ebiz.request.payment.bulk')

    name = fields.Char(string='Number')
    customer_name = fields.Many2one('res.partner', string='Customer')
    amount_due = fields.Float(string='Amount Due')
    check_box = fields.Boolean('Select')
    email_id = fields.Char(string='Email ID')
    invoice_id = fields.Char('Invoice ID')
    currency_id = fields.Many2one('res.currency', string='Company Currency')




