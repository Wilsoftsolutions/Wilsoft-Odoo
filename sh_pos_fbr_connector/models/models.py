# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from asyncio import constants
from odoo import fields, models, api, _
import requests
import json
import traceback
from odoo.exceptions import UserError
from datetime import timedelta


class FBRLog(models.Model):
    _name = 'sh.fbr.log'
    _order = 'id desc'
    _description = "FBR Log"

    name = fields.Char("POS Order Ref")
    fbr_request = fields.Text("FBR Request")
    fbr_response = fields.Text("FBR Response")
    fbr_invoice_number = fields.Char("FBR Invoice Number")
    posted_succesfull = fields.Boolean("Posted Successfully ?")


class PosSession(models.Model):
    _inherit = 'pos.session'

    sh_service_fee_journal = fields.Many2one(
        'account.move', string='Service Fee Journal')

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super(PosSession, self)._validate_session()
        orders = self.env['pos.order'].search(
            [('session_id', '=', self.id), ('sh_include_service_fee', '=', True)])

        if orders:
            service_fee = 0.00
            for each_order in orders:
                if each_order.post_data_fbr and each_order.sh_service_fee:
                    service_fee = service_fee + each_order.sh_service_fee
            journal_id = self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1)
            ref = "FBR Service Fee " + self.name
            date_tz_user = fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(self.start_at))
            date_tz_user = fields.Date.to_string(date_tz_user)

            if service_fee > 0.0:
                move_id = self.env['account.move'].sudo().create(
                    {'ref': ref, 'journal_id': journal_id.id, 'date': date_tz_user})

                if move_id:

                    fbr_service_cost_account = self.env['account.account'].search(
                        [('code', '=', '444444'), ('company_id', '=', self.env.company.id)], limit=1)
    #                 fbr_service_cost_account_id = self.env.ref('sh_pos_fbr_connector.sh_service_cost_acc').id
                    if not fbr_service_cost_account:
                        sh_user_type_id =  self.env.ref('account.data_account_type_expenses').id
                        
                        fbr_service_cost_account =  self.env['account.account'].create({'name': 'FBR Service Cost', 'code': '444444', 'user_type_id': sh_user_type_id, 'company_id':self.env.company.id })
                        # raise UserError(
                        #     "FBR service account (with code 444444) Not found !")

                    fbr_service_cost_account_id = fbr_service_cost_account.id

                    service_product = self.env.ref(
                        'sh_pos_fbr_connector.sh_demo_product_for_service_fees')
                    accounts = service_product.product_tmpl_id.get_product_accounts(
                        0)
                    if accounts == False:
                        raise UserError(
                            _("No account defined for this product: "))
                    all_lines = []
                    if fbr_service_cost_account_id:
                        vals = {

                            'credit': service_fee,
                            'debit': 0,
                            'account_id': fbr_service_cost_account_id,
                            'move_id': move_id.id,
                            'partner_id': False,
                            'name': "FBR Service Cost",
                        }
                        all_lines.append((0, 0, vals))
                    if accounts and accounts['income'] and accounts['income'].id:
                        vals = {

                            'debit': service_fee,
                            'credit': 0,
                            'account_id': accounts['income'].id,
                            'move_id': move_id.id,
                            'partner_id': False,
                            'name': "Service Fees",
                        }
                        all_lines.append((0, 0, vals))
                    if all_lines:
                        move_id.sudo().write({'line_ids': all_lines})
                        move_id.sudo().post()

                    self.write({'sh_service_fee_journal': move_id.id})


class ResCompany(models.Model):
    _inherit = 'res.company'

    strn_or_ntn = fields.Char(string="STRN")
    vat = fields.Char(related='partner_id.vat', string="NTN", readonly=False)


class PaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    payment_mode = fields.Selection([
        ('1', 'Cash'),
        ('2', 'Card'),
        ('3', 'Gift Voucher'),
        ('4', 'Loyalty Card'),
        ('5', 'Mixed'),
        ('6', 'Cheque'),
    ], required=True, default='1')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cnic = fields.Char(string="CNIC")
    ntn = fields.Char(string="NTN")


class Product(models.Model):
    _inherit = 'product.template'

    pct_code = fields.Char("PCT Code", required=True)


class Product(models.Model):
    _inherit = 'product.product'

    is_service_fee = fields.Boolean("Service Fee?")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    sh_enable_fbr_connector_feature = fields.Boolean(
        string="Enable FBR Connector")
    sh_fbr_authentication_type = fields.Selection([('sand_box', 'Sandbox'), (
        'production', 'Production')], string="FBR Authentication", default="sand_box")
    pos_id = fields.Char("POSID", required=1)
    fbr_authorization = fields.Char("FBR Header Authorization", required=1)
    sh_receipt_logo = fields.Binary("Receipt Logo", required="1")
    sh_enable_include_service = fields.Boolean(string="Include Service Fee")
    sh_service_fee = fields.Float(string="Service Fee", default="1")


class POSOrder(models.Model):
    _inherit = 'pos.order'

    fbr_request = fields.Text("FBR Request")
    fbr_respone = fields.Text("FBR Response")
    post_data_fbr = fields.Boolean("Post Data Successful ?")
    pos_reference = fields.Char(string='Receipt Ref', readonly=True, copy=True)
    invoice_number = fields.Char("Invoice Number")
    sh_include_service_fee = fields.Boolean(string="Include Service Fee")
    sh_service_fee = fields.Float(string="Service Fee")
    total_discount = fields.Float(string="Total Discount")

    def post_data_fbi(self, pos_order_data):
        #         fbr_url = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
        # Content type must be included in the header
        header = {"Content-Type": "application/json"}
        invoice_number = ''
        fbr_log_id = False
        if pos_order_data:
            try:
                for pos_order in pos_order_data:
                    order_dic = {
                        "InvoiceNumber": "",
                        "USIN": pos_order.get('name'),
                        "DateTime": (fields.Datetime.now()+timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                        "TotalBillAmount": pos_order.get('amount_total'),
                        "TotalSaleValue": pos_order.get('amount_total') - pos_order.get('amount_tax'),
                        "TotalTaxCharged": pos_order.get('amount_tax'),
                        "RefUSIN": "",
                        "Discount": pos_order.get('total_discount'),
                        "FurtherTax": 0.0,
                        #                                     "PaymentMode": 1,
                        #                                     "InvoiceType": 1,
                    }

                    if pos_order.get('amount_total') < 0.0:
                        order_dic['TotalBillAmount'] = (-1) * \
                            pos_order.get('amount_total')

                    if pos_order.get('amount_tax') < 0.0:
                        order_dic['TotalTaxCharged'] = (-1) * \
                            pos_order.get('amount_tax')

                    if (pos_order.get('amount_total') - pos_order.get('amount_tax')) < 0.0:
                        order_dic['TotalSaleValue'] = (-1) * (pos_order.get(
                            'amount_total') - pos_order.get('amount_tax'))

                    invoice_type = 1

                    if pos_order.get('amount_total'):
                        if pos_order.get('amount_total') >= 0:
                            order_dic['InvoiceType'] = 1
                        elif pos_order.get('amount_total') < 0:
                            order_dic['InvoiceType'] = 3
                            invoice_type = 3

                    if pos_order.get('statement_ids'):
                        if pos_order.get('statement_ids')[0] and pos_order.get('statement_ids')[0][2] and pos_order.get('statement_ids')[0][2]['payment_method_id']:
                            payment_obj = self.env['pos.payment.method'].search(
                                [('id', '=', pos_order.get('statement_ids')[0][2]['payment_method_id'])])
                            if payment_obj and payment_obj.payment_mode:
                                mode = payment_obj.payment_mode
                                if mode == "1":
                                    order_dic['PaymentMode'] = "1"
                                elif mode == "2":
                                    order_dic['PaymentMode'] = "2"
                                elif mode == "3":
                                    order_dic['PaymentMode'] = "3"
                                elif mode == "4":
                                    order_dic['PaymentMode'] = "4"
                                elif mode == "5":
                                    order_dic['PaymentMode'] = "5"
                                elif mode == "6":
                                    order_dic['PaymentMode'] = "6"

                    session = self.env['pos.session'].sudo().search(
                        [('id', '=', pos_order.get('pos_session_id'))])
                    if session:
                        if session.config_id:
                            config = session.config_id
                            if config.sh_fbr_authentication_type:
                                if config.sh_fbr_authentication_type == 'sand_box':
                                    fbr_url = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
                                if config.sh_fbr_authentication_type == 'production':
                                    fbr_url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
                        header.update(
                            {'Authorization': session.config_id.fbr_authorization})
                        order_dic.update({'POSID': session.config_id.pos_id})

                    if pos_order.get('partner_id'):
                        partner = self.env['res.partner'].sudo().search(
                            [('id', '=', pos_order.get('partner_id'))])

                        order_dic.update({
                            "BuyerName": partner.name,
                        })
                        if partner.mobile:
                            order_dic.update({
                                "BuyerPhoneNumber": partner.mobile,
                            })
                        if partner.cnic:
                            order_dic.update({
                                "BuyerCNIC": partner.cnic,
                            })
                        if partner.ntn:
                            order_dic.update({
                                "BuyerNTN": partner.ntn,
                            })

                    if pos_order.get('lines'):

                        items_list = []
                        total_qty = 0.0

                        for line in pos_order.get('lines'):
                            product_dic = line[2]
                            total_qty += product_dic.get('qty')

                            if 'product_id' in product_dic:
                                product = self.env['product.product'].sudo().search(
                                    [('id', '=', product_dic.get('product_id'))])
                                if product:
                                    qty = product_dic.get('qty')
                                    if product_dic.get('qty') < 0:
                                        qty = (-1) * qty

                                    price_unit = product_dic.get('price_unit')
                                    if price_unit < 0.0:
                                        price_unit = (-1) * price_unit

                                    price_subtotal = product_dic.get(
                                        'price_subtotal_incl')
                                    if price_subtotal < 0.0:
                                        price_subtotal = (-1) * price_subtotal

                                    tax_charged = product_dic.get(
                                        'price_subtotal_incl') - product_dic.get('price_subtotal')
                                    if tax_charged < 0.0:
                                        tax_charged = (-1) * tax_charged

                                    line_dic = {
                                        "ItemCode": product.default_code,
                                        "ItemName": product.name,
                                        "Quantity": qty,
                                        "PCTCode": product.pct_code,
                                        "TaxRate": round(((qty * price_unit) - price_subtotal), 2),
                                        "SaleValue": price_subtotal - tax_charged,
                                        "TotalAmount": price_subtotal,
                                        "TaxCharged": tax_charged,
                                        "InvoiceType": invoice_type,
                                        "RefUSIN": "",
                                        "Discount": 0.0,
                                        "FurtherTax": 0.0,
                                    }

                                    tax_ids = product_dic.get('tax_ids')
                                    if len(tax_ids[0][2]) > 0:
                                        tax_id = tax_ids[0][2][0]
                                        tax_rec = self.env['account.tax'].sudo().browse(
                                            int(tax_id))
                                        tax_rate = round(tax_rec.amount, 2)
                                        line_dic.update({'TaxRate': tax_rate})

                                    items_list.append(line_dic)

                        if total_qty < 0.0:
                            total_qty = (-1) * total_qty
                        order_dic.update(
                            {'Items': items_list, 'TotalQuantity': total_qty})

                    order_obj = self.search(
                        [('pos_reference', '=', pos_order['name'])])
                    fbr_log_id = self.env['sh.fbr.log'].create({
                        'name': pos_order['name'],
                        'fbr_request': json.dumps(order_dic)
                    })
                payment_response = requests.post(fbr_url, data=json.dumps(
                    order_dic), headers=header, verify=False, timeout=20)
                r_json = payment_response.json()
                invoice_number = r_json.get('InvoiceNumber')

                if fbr_log_id:
                    fbr_log_id.write(
                        {'fbr_response': r_json, 'fbr_invoice_number': invoice_number, 'posted_succesfull': True})

                if order_obj:
                    order_obj.write({'fbr_respone': r_json, 'post_data_fbr': True,
                                     'invoice_number': invoice_number, 'fbr_request': json.dumps(order_dic)})

            except Exception as e:
                values = dict(
                    exception=e,
                    traceback=traceback.format_exc(),
                )
                if fbr_log_id:
                    fbr_log_id.write(
                        {'fbr_response': values, 'posted_succesfull': False})

                return [2, json.dumps(order_dic), values]

        return [1, invoice_number, json.dumps(order_dic), payment_response]

    def post_data_to_fbr_cron(self):
        for failed_orders in self.search([('post_data_fbr', '=', False)]):
            failed_orders.post_data_to_fbr_action()

    def post_data_to_fbr_action(self):
        orders = []
        for order in self:
            if not order.post_data_fbr:
                orders.append(order.id)
                self.post_data_to_fbr(orders)

    def post_data_to_fbr(self, orders):
        #         fbr_url = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
        # Content type must be included in the header
        header = {"Content-Type": "application/json"}
        for order in orders:
            order = self.browse(order)
            try:
                if order and order.session_id and order.session_id.config_id and order.session_id.config_id.sh_enable_fbr_connector_feature and order.session_id.config_id.fbr_authorization:
                    config = order.session_id.config_id
                    if config.sh_fbr_authentication_type:
                        if config.sh_fbr_authentication_type == 'sand_box':
                            fbr_url = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
                        if config.sh_fbr_authentication_type == 'production':
                            fbr_url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
                    header.update(
                        {'Authorization': order.session_id.config_id.fbr_authorization})

                    bill_amount = order.amount_total
                    tax_amount = order.amount_tax
                    sale_amount = order.amount_total - order.amount_tax
                    order_dic = {
                        "InvoiceNumber": "",
                        "POSID": order.session_id.config_id.pos_id,
                        "USIN": order.pos_reference,
                        "DateTime": ((order.date_order)+timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                        "TotalBillAmount": bill_amount,
                        "TotalSaleValue": sale_amount,
                        "TotalTaxCharged": tax_amount,
                        "RefUSIN": "",
                        "Discount": order.total_discount,
                        "FurtherTax": 0.0,
                    }

                    if bill_amount < 0.0:
                        order_dic['TotalBillAmount'] = (-1) * bill_amount

                    if sale_amount < 0.0:
                        order_dic['TotalSaleValue'] = (-1) * sale_amount

                    if tax_amount < 0.0:
                        order_dic['TotalTaxCharged'] = (-1) * tax_amount

                    invoice_type = 1

                    if order.amount_total:
                        if order.amount_total >= 0:
                            order_dic['InvoiceType'] = 1
                            invoice_type = 1
                        elif order.amount_total < 0:
                            order_dic['InvoiceType'] = 3
                            invoice_type = 3

                    if order.payment_ids:
                        if order.payment_ids and order.payment_ids[0].payment_method_id:
                            mode = order.payment_ids[0].payment_method_id.payment_mode
                            if mode == "1":
                                order_dic['PaymentMode'] = "1"
                            elif mode == "2":
                                order_dic['PaymentMode'] = "2"
                            elif mode == "3":
                                order_dic['PaymentMode'] = "3"
                            elif mode == "4":
                                order_dic['PaymentMode'] = "4"
                            elif mode == "5":
                                order_dic['PaymentMode'] = "5"
                            elif mode == "6":
                                order_dic['PaymentMode'] = "6"

                    if order.partner_id:
                        order_dic.update({
                            "BuyerName": order.partner_id.name,
                        })
                        if order.partner_id.mobile:
                            order_dic.update({
                                "BuyerPhoneNumber": order.partner_id.mobile,
                            })
                        if order.partner_id.cnic:
                            order_dic.update({
                                "BuyerCNIC": order.partner_id.cnic,
                            })
                        if order.partner_id.ntn:
                            order_dic.update({
                                "BuyerNTN": order.partner_id.ntn,
                            })

                    if order.lines:
                        items_list = []
                        total_qty = 0.0
                        for line in order.lines:
                            total_qty += line.qty
                            qty = line.qty
                            if qty < 0:
                                qty = (-1) * qty

                            price_unit = line.price_unit
                            if price_unit < 0.0:
                                price_unit = (-1) * price_unit

                            price_subtotal = line.price_subtotal_incl
                            if price_subtotal < 0.0:
                                price_subtotal = (-1) * price_subtotal

                            tax_charged = line.price_subtotal_incl - line.price_subtotal
                            if tax_charged < 0.0:
                                tax_charged = (-1) * tax_charged

                            line_dic = {
                                "ItemCode": line.product_id.default_code,
                                "ItemName": line.product_id.name,
                                "Quantity": qty,
                                "PCTCode": line.product_id.pct_code,
                                "TaxRate": round(((qty * price_unit) - price_subtotal), 2),
                                "SaleValue": price_subtotal - tax_charged,
                                "TotalAmount": price_subtotal,
                                "TaxCharged": tax_charged,
                                "InvoiceType": invoice_type,
                                "RefUSIN": "",
                                "Discount": 0.0,
                                "FurtherTax": 0.0,
                            }
                            if line.tax_ids:
                                tax_rate = round(line.tax_ids[0].amount, 2)
                                line_dic.update({'TaxRate': tax_rate})

                            items_list.append(line_dic)

                        if total_qty < 0.0:
                            total_qty = (-1) * total_qty

                        order_dic.update({
                            "Items": items_list,
                            "TotalQuantity": total_qty
                        })
                        fbr_log_id = self.env['sh.fbr.log'].create({
                            'name': order.pos_reference,
                            'fbr_request': json.dumps(order_dic)
                        })
                    payment_response = requests.post(fbr_url, data=json.dumps(
                        order_dic), headers=header, verify=False, timeout=20)
                    r_json = payment_response.json()
                    invoice_number = r_json.get('InvoiceNumber')

                    if fbr_log_id:
                        fbr_log_id.write(
                            {'fbr_response': r_json, 'fbr_invoice_number': invoice_number, 'posted_succesfull': True})

                    order.write({'fbr_respone': r_json, 'post_data_fbr': True,
                                 'invoice_number': invoice_number, 'fbr_request': json.dumps(order_dic)})

            except Exception as e:
                values = dict(
                    exception=e,
                    traceback=traceback.format_exc(),
                )
                if fbr_log_id:
                    fbr_log_id.write(
                        {'fbr_response': values, 'posted_succesfull': False})
                order.write(
                    {'fbr_respone': values, 'fbr_request': json.dumps(order_dic)})

    @api.model
    def _order_fields(self, ui_order):
        res = super(POSOrder, self)._order_fields(ui_order)
        res['invoice_number'] = ui_order.get('invoice_number', False)
        res['post_data_fbr'] = ui_order.get('post_data_fbr', False)
        res['fbr_respone'] = ui_order.get('fbr_respone', False)
        res['fbr_request'] = ui_order.get('fbr_request', False)
        res['total_discount'] = ui_order.get('total_discount', 0.00)
        if ui_order.get('sh_include_service_fee'):
            res['sh_include_service_fee'] = ui_order.get(
                'sh_include_service_fee', False)
            res['sh_service_fee'] = ui_order.get('sh_service_fee', False)
        return res
