# -*- coding: utf-8 -*-

import pprint
import logging
import werkzeug
from werkzeug import urls, utils
from odoo.addons.web.controllers.main import Session
from odoo.addons.website_sale.controllers.main import WebsiteSale
# from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from datetime import date

_logger = logging.getLogger(__name__)


class EbizchargeController(http.Controller):
    _approved_url = '/payment/ebizcharge/approved'
    _decline_url = '/payment/ebizcharge/cancel'
    _error_url = '/payment/ebizcharge/error'

    @http.route([
        '/payment/ebizcharge/approved/',
        '/payment/ebizcharge/cancel/',
    ], type='http', auth='public', csrf=False)
    def ebizcharge_form_feedback(self, **post):
        _logger.info('EBizCharge: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'ebizcharge')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # EBizCharge is expecting a response to the POST sent by their server.
        # This response is in the form of a URL that EBizCharge will pass on to the
        # client's browser to redirect them to the desired location need javascript.
        odooInvoiceNumber = post.get('TransactionLookupKey').split('-')[0]
        odooInvoice = request.env['account.move'].sudo().search([('name', '=', odooInvoiceNumber)])
        if odooInvoice:
            ebiz = request.env['ebiz.charge.api'].sudo().get_ebiz_charge_obj()
            if odooInvoice.payment_internal_id:
                ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': odooInvoice.payment_internal_id,

                })

        return utils.redirect(urls.url_join(base_url, "/payment/process"))

    @http.route(['/payment/ebizcharge/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def ebizcharge_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        token = False
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        
        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
            website_id = request.website_routing
            token = acquirer.with_context({'website': website_id}).s2s_process(kwargs)
        except ValidationError as e:
            _logger.exception(e)
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
                message = msg + ', '.join(message['missing_fields']) + '. '
                if request.env.user._is_public():
                    message += _("Please sign in to complete your profile.")
                    # update message if portal mode = b2b
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += _("If you don't have any account, please ask your salesperson to update your profile. ")
                else:
                    message += _("Please complete your profile.")

            return {
                'error': message
            }

        if not token:
            res = {
                'result': False,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            '3d_secure': False,
            'verified': token.verified,
        }
        return res

    @http.route(['/payment/ebizcharge/get/token'], type='json', auth='public', csrf=False)
    def ebizcharge_get_token_info(self, **kwargs):
        return request.env['payment.token'].get_payment_token_information(kwargs['pm_id'])

    @http.route(['/payment/ebizcharge/s2s/create'], type='http', auth='public')
    def ebizcharge_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        acquirer.s2s_process(post)
        return utils.redirect(post.get('return_url', '/'))

    @http.route('/payment/ebizcharge', type='http', auth="public", website=True, csrf=False)
    def ebizcharge_payment(self, **post):
        """ EBizCharge Payment Controller """
        _logger.info('Beginning ebizcharge with post data %s', pprint.pformat(post))  # debug
        if post.get('DocumentTypeId') == 'Sales order':
            odooSo = request.env['sale.order'].sudo().search([('name', '=', post['InvoiceNumber'])])
            if not odooSo.ebiz_internal_id:
                odooSo.sync_to_ebiz()
            lines = odooSo.order_line
            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': post['FromEmail'],
                'FromName': post['FromName'],
                'EmailSubject': post['EmailSubject'],
                'EmailAddress': post['EmailAddress'],
                'EmailTemplateID': post['EmailTemplateID'],
                'EmailTemplateName': post['EmailTemplateName'],
                'ShowSavedPaymentMethods': True,
                'CustFullName': post['CustFullName'],
                'TotalAmount': odooSo.amount_total,
                'AmountDue': odooSo.amount_total,
                'CustomerId': post['CustomerId'],
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': False,
                'TaxAmount': odooSo.amount_tax,
                'SoftwareId': 'Odoo CRM',
                'Description': post['Description'],
                'DocumentTypeId': post['DocumentTypeId'],
                'InvoiceNumber': post['InvoiceNumber'],
                'TransactionLookupKey': post['TransactionLookupKey'],
                'BillingAddress': {
                    "FirstName": post['FirstName'],
                    "LastName": post['LastName'],
                    "Address1": post['Address1'],
                    "City": post['City'],
                    "State": post['State'],
                    "ZipCode": post['ZipCode'],
                    "Country": post['Country'],
                },
                'ApprovedURL': post['ApprovedURL'],
                'DeclinedURL': post['DeclinedURL'],
                'ErrorURL': post['ErrorURL'],
                'DisplayDefaultResultPage': int(post['DisplayDefaultResultPage']),
                'SoNum': post['InvoiceNumber'],
                "LineItems": self._transaction_lines(lines),
            }
        else:
            odooInvoice = request.env['account.move'].sudo().search([('name', '=', post['InvoiceNumber'])])
            if not odooInvoice.ebiz_internal_id:
                odooInvoice.sync_to_ebiz()
            lines = odooInvoice.invoice_line_ids
            ePaymentForm = {
                'FormType': 'EmailForm',
                'FromEmail': post['FromEmail'],
                'FromName': post['FromName'],
                'EmailSubject': post['EmailSubject'],
                'EmailAddress': post['EmailAddress'],
                'EmailTemplateID': post['EmailTemplateID'],
                'EmailTemplateName': post['EmailTemplateName'],
                'ShowSavedPaymentMethods': True,
                'CustFullName': post['CustFullName'],
                'TotalAmount': odooInvoice.amount_total,
                'AmountDue': odooInvoice.amount_residual,
                'CustomerId': post['CustomerId'],
                'ShowViewInvoiceLink': True,
                'SendEmailToCustomer': False,
                'TaxAmount': odooInvoice.amount_tax,
                'SoftwareId': 'Odoo CRM',
                'Description': post['Description'],
                'DocumentTypeId': post['DocumentTypeId'],
                'InvoiceNumber': post['InvoiceNumber'],
                'TransactionLookupKey': post['TransactionLookupKey'],
                'BillingAddress': {
                    "FirstName": post['FirstName'],
                    "LastName": post['LastName'],
                    "Address1": post['Address1'],
                    "City": post['City'],
                    "State": post['State'],
                    "ZipCode": post['ZipCode'],
                    "Country": post['Country'],
                },
                'ApprovedURL': post['ApprovedURL'],
                'DeclinedURL': post['DeclinedURL'],
                'ErrorURL': post['ErrorURL'],
                'DisplayDefaultResultPage': int(post['DisplayDefaultResultPage']),
                'InvoiceInternalId': odooInvoice.ebiz_internal_id,
                "LineItems": self._transaction_lines(lines),
            }
        ebiz = request.env['ebiz.charge.api'].sudo().get_ebiz_charge_obj()
        form_url = ebiz.client.service.GetEbizWebFormURL(**{
            'securityToken': ebiz._generate_security_json(),
            'ePaymentForm': ePaymentForm
        })
        if post.get('DocumentTypeId') == 'Sales order':
            odooSalesOrder = request.env['sale.order'].sudo().search([('name', '=', post['InvoiceNumber'])])
            if odooSalesOrder:
                odooSalesOrder.write({
                    'payment_internal_id': form_url.split('?pid=')[1]
                })
        else:
            odooInvoice = request.env['account.move'].sudo().search([('name', '=', post['InvoiceNumber'])])
            if odooInvoice:
                odooInvoice.write({
                    'payment_internal_id': form_url.split('?pid=')[1]
                })
        return werkzeug.utils.redirect(form_url)

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


class EbizChargeSession(Session):

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        user_id = request.session['uid']
        odooUser = request.env['res.users'].browse(user_id).ensure_one()
        odooPartner = odooUser.sudo().partner_id
        odooPartner.payment_token_ids.with_context({'donot_sync': True}).sudo().unlink()
        return super(EbizChargeSession, self).logout(redirect=redirect)


class EbizChargeWebsiteSale(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        res = super(EbizChargeWebsiteSale, self).shop_payment(post=post)
        if res.status_code == 200:
            showACH = request.website.merchant_data
            showCreditCards = request.website.allow_credit_card_pay
            allowedCommands = request.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.ebiz_website_allowed_command')
            authOnly = True if allowedCommands == 'pre-auth' else False
            odooPartner = request.env['res.partner'].sudo().browse(res.qcontext['partner'].id).ensure_one()
            if odooPartner:
                odooPartner.sudo().with_context({'donot_sync': True, 'website': request.website.id}).ebiz_get_payment_methods()
            payment_tokens = odooPartner.payment_token_ids
            payment_tokens |= odooPartner.commercial_partner_id.sudo().payment_token_ids
            res.qcontext['tokens'] = payment_tokens.filtered(lambda r: r.create_uid == request.env.user)
            # res.qcontext['showACH'] = showACH
            # res.qcontext['showCreditCards'] = showCreditCards
            # res.qcontext['authOnly'] = authOnly
            # res.qcontext['logIn'] = True if request.session['session_token'] else False
            res.qcontext['showACH'] = True
            res.qcontext['showCreditCards'] = True
            res.qcontext['authOnly'] = False
            res.qcontext['logIn'] = True
        return res

    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token(self, pm_id=None, **kwargs):
        """ Method that handles payment using saved tokens

        :param int pm_id: id of the payment.token that we want to use to pay.
        """
        order = request.website.sale_get_order()
        # do not crash if the user has already paid and try to pay again
        if not order:
            return request.redirect('/shop/?error=no_order')

        if 'security-code' not in kwargs:
            return request.redirect('/shop/?error=no_security_code')

        assert order.partner_id.id != request.website.partner_id.id

        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/shop/?error=invalid_token_id')

        # We retrieve the token the user want to use to pay
        if not request.env['payment.token'].sudo().search_count([('id', '=', pm_id)]):
            return request.redirect('/shop/?error=token_not_found')

        # Create transaction
        vals = {'payment_token_id': pm_id, 'return_url': '/shop/payment/validate',
                'security_code': kwargs['security-code']}

        tx = order._create_payment_transaction(vals)
        PaymentProcessing.add_payment_transaction(tx)
        return request.redirect('/payment/process')

