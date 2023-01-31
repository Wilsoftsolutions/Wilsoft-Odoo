from odoo import fields, models,api, _
import json
from collections import defaultdict
from ..models.ebiz_charge import message_wizard


class CustomMessageWizard(models.TransientModel):
    _name = 'wizard.process.credit.transaction'

    sale_order_id = fields.Many2one('sale.order')
    invoice_id = fields.Many2one('account.move')
    # picking_id = fields.Many2one('stock.picking')
    sale_id = fields.Many2one('sale.order')
    partner_id = fields.Many2one('res.partner')
    method_id = fields.Many2one('payment.token')
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True)
    allow_partial_payment = fields.Boolean('Allow partial payment', default = False)

    def process_credit_transaction(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        vals = {
            'acquirer_id': self.env.ref('payment_ebizcharge.payment_acquirer_ebizcharge').id,
        }
        # if self.allow_partial_payment:
        if True:
            if self.invoice_id:
                trans = self.invoice_id.reversed_entry_id.done_transaction_ids
                resp = ebiz.run_credit_transaction(self.invoice_id, self.method_id, trans.acquirer_reference)
                if resp['ResultCode'] == "A":
                    trans = self.invoice_id._create_payment_transaction(vals)
                    trans.write({'payment_token_id': self.method_id,
                     'acquirer_reference': resp['RefNum'], 
                     'date': fields.Datetime.now()})
                    trans._set_transaction_done()
                    self.invoice_id.process_refund_payment()
                    return message_wizard(_('Transaction has been successfully credited!'))
                else:
                    return message_wizard(_('Transaction Has been declined, because '+resp['Error']), 'Transaction Failed')
            else:
                resp = self.run_credit_transaciton_on_sale_order()
                if resp['ResultCode'] == "A":
                    # trans = self.invoice_id._create_payment_transaction(vals)
                    # trans.write({'payment_token_id': self.method_id,
                    #  'acquirer_reference': resp['RefNum'], 
                    #  'date': fields.Datetime.now()})
                    # trans._set_transaction_done()
                    self.picking_id.ebiz_refund_refnum = resp['RefNum']
                    self.picking_id.ebiz_credit_done = True
                    return message_wizard(_('Transaction has been successfully refunded!'))
                else:
                    return message_wizard(_('Transaction has been declined because %s'%resp['Error']))

        else:
            transaction_id = self.invoice_id.invoice_line_ids.sale_line_ids.order_id.done_transaction_ids
            transaction_id = order.done_transaction_ids
            payment_obj['ref_num'] = transaction_id.acquirer_reference
            transaction_id.s2s_do_refund(**payment_obj)
            return message_wizard('Transaction has been Denined!')

    def run_credit_transaciton_on_sale_order(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        trans_obj = self.get_customer_transaction_object()
        params = {
            "securityToken": ebiz._generate_security_json(),
            "custNum": self.partner_id.ebizcharge_customer_token,
            "paymentMethodID": self.method_id.ebizcharge_profile,
            "tran": trans_obj
        }
        resp = ebiz.client.service.runCustomerTransaction(**params)
        return resp

    def get_customer_transaction_object(self):
        sale = self.picking_id.sale_id
        ref = sale.done_transaction_ids.acquirer_reference
        return {
            "isRecurring":False,
            "IgnoreDuplicate": False,
            "InventoryLocation": "",
            "Details": self._get_transaction_details(),
            "Software":'Odoo CRM',
            "MerchReceipt": True,
            "CustReceiptName":'',
            "CustReceiptEmail":'',
            "CustReceipt": False,
            "ClientIP":'',
            "CardCode": self.method_id.card_code,
            "Command": 'CREDIT',
            # "RefNum": ref,
            "LineItems": self._transaction_lines(),           
        }

    def _get_transaction_details(self):
        sale = self.picking_id.sale_id
        order_id = sale.name
        invoice_id = sale.invoice_ids[0].name if sale.invoice_ids else sale.name
        po = sale.client_order_ref or sale.name
        amounts = self._compute_amount()
        return {
            'OrderID': order_id,
            'Invoice': invoice_id or "",
            'PONum': po,
            'Description': 'description',
            'Amount': amounts['price_total'],
            'Tax': amounts['price_tax'],
            'Shipping': 0,
            'Discount': 0,
            'Subtotal': amounts['price_subtotal'],
            'AllowPartialAuth': False,
            'Tip': 0,
            'NonTax': False,
            'Duty': 0,
        }

    def _transaction_lines(self):
        item_list = []
        for line in self.picking_id.move_line_ids_without_package:
            item_list.append(self._transaction_line(line))
        return {'LineItem':item_list}

    def _transaction_line(self, p_line):
        sale = self.picking_id.sale_id
        line = sale.order_line.filtered(lambda x: x.product_id.id == p_line.product_id.id)
        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        tax_ids = line.tax_ids if hasattr(line, 'tax_ids') else line.tax_id
        price_tax = line.price_tax if hasattr(line, 'price_tax') else 0
        sale = self.picking_id.sale_id
        return {
            'SKU': line.product_id.id,
            'ProductName': line.product_id.name,
            'Description': line.name,
            'UnitPrice': line.price_unit,
            'Taxable': True if tax_ids else False,
            'TaxAmount': str(price_tax),
            'Qty': str(p_line.qty_done)
        }

    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        amounts = defaultdict(lambda: 0)
        price_tax = 0
        price_total = 0
        sale = self.picking_id.sale_id
        for line_picking in self.picking_id.move_line_ids_without_package:
            line = sale.order_line.filtered(lambda x: x.product_id.id == line_picking.product_id.id)
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line_picking.qty_done, product=line.product_id, partner=line.order_id.partner_shipping_id)
            amounts['price_tax'] += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            amounts['price_total'] += taxes['total_included']
            amounts['price_subtotal'] += taxes['total_excluded']
        return amounts