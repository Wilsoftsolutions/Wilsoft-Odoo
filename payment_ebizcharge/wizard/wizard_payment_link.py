# -*- coding: utf-8 -*-

from werkzeug import urls
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import ustr, consteq, float_compare


class EbizPaymentLinkWizard(models.TransientModel):
    _name = "ebiz.payment.link.wizard"
    _description = "Generate Payment Link"

    @api.model
    def default_get(self, fields):
        res = super(EbizPaymentLinkWizard, self).default_get(fields)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        res.update({'res_id': res_id, 'res_model': res_model})
        amount_field = 'amount_residual' if res_model == 'account.move' else 'amount_total'
        if res_id and res_model == 'account.move':
            record = self.env[res_model].browse(res_id)
            res.update({
                'description': record.payment_reference,
                'amount': record[amount_field],
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record[amount_field],
            })
        return res

    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    amount_max = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    partner_email = fields.Char(related='partner_id.email')
    link = fields.Char(string='Payment Link')
    description = fields.Char('Payment Ref')

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

    @api.onchange('amount', 'description')
    def _onchange_amount(self):
        if float_compare(self.amount_max, self.amount, precision_rounding=self.currency_id.rounding or 0.01) == -1:
            raise ValidationError(_("Please set an amount smaller than %s.") % (self.amount_max))
        if self.amount <= 0:
            raise ValidationError(_("The value of the payment amount must be positive."))

    def generate_link(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            res_id = self._context.get('active_id')
            res_model = self._context.get('active_model')
            record = self.env[res_model].browse(res_id)

            fname = record.partner_id.name.split(' ')
            lname = ''
            for name in range(1, len(fname)):
                lname += fname[name]

            address = ''
            if record.partner_id.street:
                address += record.partner_id.street
            if record.partner_id.street2:
                address += ' ' + record.partner_id.street2

            try:
                lines = record.order_line
            except AttributeError:
                lines = record.invoice_line_ids

            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': record.env.user.email,
                'FromName': record.env.user.name,
                'EmailSubject': self.select_template.template_subject,
                'EmailAddress': self.partner_email,
                'EmailTemplateID': self.select_template.template_id,
                'EmailTemplateName': self.select_template.name,
                'ShowSavedPaymentMethods': True,
                'CustFullName': record.partner_id.name,
                'TotalAmount': record.amount_total,
                'AmountDue': self.amount,
                'ShippingAmount': self.amount,
                'CustomerId': record.partner_id.ebiz_customer_id or record.partner_id.id,
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': False,
                'TaxAmount': record.amount_tax,
                'SoftwareId': 'Odoo CRM',
                'InvoiceInternalId': record.ebiz_internal_id,
                'Description': 'Invoice',
                'DocumentTypeId': 'Invoice',
                'InvoiceNumber': str(record.id) if str(record.name) == '/' else str(record.name),
                'BillingAddress': {
                    "FirstName": fname[0],
                    "LastName": lname,
                    "CompanyName": record.partner_id.company_name if record.partner_id.company_name else '',
                    "Address1": address,
                    "City": record.partner_id.city if record.partner_id.city else '',
                    "State": record.partner_id.state_id.code or 'CA',
                    "ZipCode": record.partner_id.zip or '',
                    "Country": record.partner_id.country_id.code or 'US',
                },
                "LineItems": self._transaction_lines(lines),
            }
            if record.partner_id.ebiz_customer_id:
                ePaymentForm['CustomerId'] = record.partner_id.ebiz_customer_id

            ePaymentForm[
                'Date'] = record.invoice_date if record.invoice_date else record.invoice_date_due if record.invoice_date_due else ''

            form_url = ebiz.client.service.GetEbizWebFormURL(**{
                'securityToken': ebiz._generate_security_json(),
                'ePaymentForm': ePaymentForm
            })

            record.save_payment_link = form_url
            record.payment_internal_id = form_url.split('=')[1]

            return {'type': 'ir.actions.act_window',
                    'name': _('Copy Payment Link'),
                    'res_model': 'ebiz.payment.link.copy',
                    'target': 'new',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'context': {
                        'default_link': form_url,
                    },
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


class EbizPaymentLink(models.TransientModel):
    _name = "ebiz.payment.link.copy"
    _description = "Copy Payment Link"

    link = fields.Char(string='Payment Link')
