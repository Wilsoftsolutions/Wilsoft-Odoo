# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager


class TransactionPortal(CustomerPortal):

    def getTransactionData(self, order):
        filters_list = []
        TransactionHistory = request.env['transaction.history'].sudo()
        filters_list.append(TransactionHistory.sudo()._get_filter_object('OrderID', 'eq', order))
        transactions = TransactionHistory._get_transactions_data(filters=filters_list)
        return transactions

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        res = super(TransactionPortal, self).portal_order_page(order_id, report_type=report_type,
                                                               access_token=access_token, message=message,
                                                               download=download, **kw)
        if res.status_code == 200:
            transactionObj = request.env['transaction.history']
            if 'search' in kw and kw['search'] != "":
                transactions = transactionObj.search([('invoice_id', '=', res.qcontext['sale_order'].name)])
                if not transactions:
                    response = self.getTransactionData(res.qcontext['sale_order'].name)
                    transactionObj.sudo().search([]).unlink()
                    transactionObj.sudo().create(response)
                    transactions = transactionObj.search([('invoice_id', '=', res.qcontext['sale_order'].name)])
                transactions = transactions.search([('ref_no', '=', kw['search'])])
            else:
                response = self.getTransactionData(res.qcontext['sale_order'].name)
                transactionObj.sudo().search([]).unlink()
                transactionObj.sudo().create(response)
                transactions = transactionObj.search([('invoice_id', '=', res.qcontext['sale_order'].name)])
            res.qcontext.update({
                'transactions': transactions,
            })
        return res
    
    
class EbizWebsitePayment(PaymentPortal):
    @http.route(['/my/payment_method'], type='http', auth="user", website=True)
    def payment_method(self, **kwargs):
        res = super(EbizWebsitePayment, self).payment_method(kwargs=kwargs)
        if res.status_code == 200:
            showACH = request.website.merchant_data
            showCreditCards = request.website.allow_credit_card_pay
            allowedCommands = request.env['ir.config_parameter'].sudo().get_param(
                'payment_ebizcharge.ebiz_website_allowed_command')
            authOnly = True if allowedCommands == 'pre-auth' else False
            odooPartner = request.env['res.partner'].browse(res.qcontext['partner_id']).ensure_one()
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

    @http.route('/payment/pay', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def payment_pay(self, reference=None, amount=None, currency_id=None, partner_id=None, company_id=None,
                    acquirer_id=None, access_token=None, invoice_id=None, **kwargs):

        res = super(EbizWebsitePayment, self).payment_pay(reference=reference, amount=amount, currency_id=currency_id,
                                                          partner_id=partner_id, company_id=company_id,
                                                          acquirer_id=acquirer_id, access_token=access_token,
                                                          invoice_id=invoice_id, **kwargs)
        if res.status_code == 200:
            odooInvoice = request.env['account.move'].sudo().search([('name', '=', reference),
                                                                     ('payment_state', '=', 'paid')])
            if odooInvoice:
                return request.render("payment_ebizcharge.payment_already_paid")
        return res
