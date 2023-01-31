# -*- coding: utf-8 -*-

from zeep import Client
# from suds.client import Client


def message_wizard(message, title="Success"):
    context = dict()
    context['message'] = message
    return {
        'name': title,
        'view_type': 'form',
        'view_mode': 'form',
        'views': [[False, 'form']],
        'res_model': 'message.wizard',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'target': 'new',
        'context': context
    }


sample_get_customer = {
    'securityToken':{
        'SecurityId': '0814c940-5ea6-425e-8343-994c126caa13',
        'UserId': 'odoo1',
        'Password': 'odoo1'
    },
    'customerId':"123456"
}
class EbizChargeAPI():
    """
    EbizCharge API Middleware
    """
    def __init__(self, security_key, user_id, password):
        """
        Initialize EbizCharge Object 
        """
        self.url = 'https://soap.ebizcharge.net/eBizService.svc?singleWsdl'
        self.client = Client(wsdl=self.url)
        # self.client = Client(self.url)
        self.security_key = security_key
        self.user_id = user_id
        self.password = password

    def _generate_security_json(self):
        security_json = {
            'SecurityId': self.security_key,
            'UserId': self.user_id,
            'Password': self.password
        }
        return security_json

    def _add_customer_params(self, partner):
        addr = partner.address_get(['delivery', 'invoice'])
        name_array = partner.name.split(' ')
        first_name = name_array[0]
        if len(name_array) >= 2:
            last_name = " ".join(name_array[1:])
        else:
            last_name = ""

        customer = {
            "MerchantId": "",
            "CustomerInternalId": "",
            "CustomerId": partner.id,
            "FirstName": first_name,
            "LastName": last_name,
            "CompanyName": partner.parent_id.name if partner.parent_id else partner.name or "",
            "Phone": partner.phone or "",
            "CellPhone": partner.mobile or "",
            "Fax": "",
            "Email": partner.email or "",
            "WebSite": partner.website or "",
            'BillingAddress': self._get_customer_address(partner.browse(addr['invoice'])),
            'ShippingAddress': self._get_customer_address(partner.browse(addr['delivery']))
        }
        sync_object = {
            'securityToken': self._generate_security_json(),
            'customer': customer
        }
        return sync_object

    def _get_customer_address(self, partner):
        name_array = partner.name.split(' ')
        first_name = name_array[0]
        if len(name_array) >= 2:
            last_name = " ".join(name_array[1:])
        else:
            last_name = ""
        Address = {
            "FirstName": first_name,
            "LastName": last_name,
            "CompanyName": partner.name if partner.company_type == "company" else partner.parent_id.name or "",
            "Address1": partner.street or "",
            "Address2": partner.street2 or "",
            "City": partner.city or "",
            "State": partner.state_id.code or "",
            "ZipCode": partner.zip or "",
            "Country": partner.country_id.code or "US"
        }
        return Address

    def add_customer(self, partner):
        customer_params = self._add_customer_params(partner)
        res = self.client.service.AddCustomer(**customer_params)
        if res['ErrorCode'] == 2:
            get_resp = self.get_customer(partner.id)
            partner.write({
                'ebiz_internal_id': get_resp['CustomerInternalId'],
                "ebizcharge_customer_token": get_resp['CustomerToken']})
            res = self.update_customer(partner)

        return res

    def _update_customer_params(self, partner):
        customer_params = self._add_customer_params(partner)
        customer_params['customerId'] = partner.id
        return customer_params

    def _get_customer_params(self, partner_id):
        return {
            'securityToken': self._generate_security_json(),
            'customerId': partner_id
        }

    def update_customer(self, partner):
        customer_params = self._update_customer_params(partner)
        return self.client.service.UpdateCustomer(**customer_params)


    def get_customer(self, partner_id):
        customer_params = self._get_customer_params(partner_id)
        res = self.client.service.GetCustomer(**customer_params)
        return res

    def get_customer_token(self, partner_id):
        customer_params = {
            'securityToken': self._generate_security_json(),
            'CustomerId': partner_id
        }
        res = self.client.service.GetCustomerToken(**customer_params)
        return res

    def _so_line_params(self, line, item_no):
        item = {
            "ItemId": line.product_id.id,
            "Name": line.product_id.name,
            "Description": line.product_id.description,
            "UnitPrice": line.price_unit,
            "Qty": line.product_uom_qty,
            # "Taxable": True if line.product_id.taxes_id else False,
            "Taxable": False,
            "TaxRate": 0,
            "GrossPrice": 0,
            "WarrantyDiscount": 0,
            "SalesDiscount": 0,
            "UnitOfMeasure": line.product_uom.name,
            "TotalLineAmount": line.price_subtotal,
            # "TotalLineTax": line.price_tax,
            "TotalLineTax": 0,
            "ItemLineNumber": item_no,
        }
        return item 

    def _so_lines_params(self, lines):
        lines_list = []
        for i, line in enumerate(lines):
            lines_list.append(self._so_line_params(line, i+1))
        return lines_list

    def _add_so_params(self, order):
        array_of_items = self.client.get_type('ns0:ArrayOfItem')
        order = {
            "CustomerId": order.partner_id.id,
            "SubCustomerId":"",
            "SalesOrderNumber": order.name,
            "Date": str(order.date_order.date()),
            "Amount": order.amount_total,
            "DueDate": str(order.date_order.date()),
            "AmountDue": order.amount_total,
            # "SoNum": order.name,
            "TypeId": "Invoice",
            "Software": "Odoo CRM",
            "NotifyCustomer": False,
            # "Currency": order.currency_id.name,
            "EmailTemplateID": "",
            "URL": "",
            "TotalTaxAmount": order.amount_tax,
            "UniqueId": "",
            "Description": "Sale Order" if order.state in ['done','sale'] else "Quotation",
            "CustomerMessage": "",
            "Memo": "",
            # "ShipDate": str(order.commitment_date.date()) if order.commitment_date else str(order.expected_date.date()),
            "ShipVia": "",
            "SalesRepId": order.user_id.id,
            "TermsId": "",
            "IsToBeEmailed": 0,
            "IsToBePrinted": 0,
            "Items": array_of_items(self._so_lines_params(order.order_line))
        }
        return order

    def _add_order_params(self, order):
        sync_object = {
            'securityToken': self._generate_security_json(),
            'salesOrder': self._add_so_params(order)
        }
        return sync_object

    def sync_sale_order(self,order):
        so_params = self._add_order_params(order)
        res = self.client.service.AddSalesOrder(**so_params)
        return res

    def _update_sale_order_params(self, order):
        so_params = self._add_order_params(order)
        so_params.update({
                'customerId': order.partner_id.id,
                'salesOrderNumber': order.name,
                'salesOrderInternalId': order.ebiz_internal_id
            })
        return so_params

    def update_sale_order(self, order):
        so_params = self._update_sale_order_params(order)
        res = self.client.service.UpdateSalesOrder(**so_params)
        return res
    
    def get_sales_order(self, order):
        params = {
            'securityToken': self._generate_security_json(),
            'customerId': order.partner_id.id,
            'salesOrderNumber': order.name,
            'salesOrderInternalId': order.ebiz_internal_id,
        }
        return self.client.service.GetSalesOrder(**params)

    def search_sale_order(self, order):
        pass
        
    def _payment_profile_credit_card(self, profile):
        credit_card =  {
            "AccountHolderName": profile.account_holder_name,
            "MethodType": "CreditCard",
            # "SecondarySort": profile.secondary_sort,
            # "MethodName": profile.name,
            "CardExpiration": "%s-%s"%(profile.card_exp_year, profile.card_exp_month),
            "AvsStreet": profile.avs_street,
            "AvsZip": profile.avs_zip,
            "CardCode": profile.card_code,
            # "CardType": profile.card_type,
            "Created":profile.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
            "Modified":profile.write_date.strftime('%Y-%m-%dT%H:%M:%S')
            }
        # if profile.is_default:
        #     credit_card['SecondarySort'] = '0'
        if not 'xxx' in profile.card_number:
            credit_card['CardNumber'] = profile.card_number
        if profile.ebizcharge_profile:
            credit_card['MethodID'] = profile.ebizcharge_profile

        return credit_card

    def _payment_profile_bank(self, profile):

        bank_profile = {
            "AccountHolderName": profile.account_holder_name,
            "MethodType": "ACH",
            # "MethodName": profile.name,
            "AccountType": profile.account_type,
            # "Account": profile.account_number,
            "Routing": profile.routing,
            # "DriversLicense": profile.drivers_license,
            # "DriversLicenseState": profile.drivers_license_state,
            "Created":profile.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
            "Modified":profile.write_date.strftime('%Y-%m-%dT%H:%M:%S')
        }
        # if profile.is_default:
        #     bank_profile['SecondarySort'] = '0'
        if not 'xxx' in profile.account_number:
            bank_profile['Account'] = profile.account_number
        if profile.ebizcharge_profile:
            bank_profile['MethodID'] = int(profile.ebizcharge_profile)

        return bank_profile

    def _generate_payment_profile(self, profile, p_type='credit'):
        return {
            'securityToken': self._generate_security_json(),
            'customerInternalId': profile.partner_id.ebiz_internal_id,
            "paymentMethodProfile": self._payment_profile_credit_card(profile) if p_type == "credit" else self._payment_profile_bank(profile)
        }

    def add_customer_payment_profile(self, profile, p_type='credit'):
        sync_params = self._generate_payment_profile(profile, p_type)
        customer_profile = self.client.service.AddCustomerPaymentMethodProfile(**sync_params)
        return customer_profile

    def update_customer_payment_profile(self, profile, p_type='credit'):
        sync_params = self._generate_payment_profile(profile, p_type)
        del sync_params['customerInternalId']
        sync_params['customerToken'] = profile.partner_id.ebizcharge_customer_token
        return self.client.service.UpdateCustomerPaymentMethodProfile(**sync_params)

    def delete_customer_payment_profile(self, profile):
        params = {
            'securityToken': self._generate_security_json(),
            'customerToken': profile.partner_id.ebizcharge_customer_token,
            'paymentMethodId': profile.ebiz_internal_id
        }
        resp = self.client.service.DeleteCustomerPaymentMethodProfile(**params)
        return resp

    def _invoice_line_params(self, line, item_no):
        item = {
            "ItemId": line.product_id.id,
            "Name": line.product_id.name,
            "Description": line.product_id.name,
            "UnitPrice": line.price_unit,
            "Qty": line.quantity,
            # "Taxable": True if line.product_id.taxes_id else False,
            "Taxable": False,
            "TaxRate": 0,
            "GrossPrice": 0,
            "WarrantyDiscount": 0,
            "SalesDiscount": 0,
            "UnitOfMeasure": line.product_id.uom_id.name,
            "TotalLineAmount": line.price_subtotal,
            # "TotalLineTax": line.tax_base_amount,
            "TotalLineTax": 0,
            "ItemLineNumber": item_no
        }
        return item 
    
    def _invoice_lines_params(self, invoice_lines):
        lines_list = []
        for i,line in enumerate(invoice_lines):
            lines_list.append(self._invoice_line_params(line, i+1))
        array_of_items = self.client.get_type('ns0:ArrayOfItem')
        return array_of_items(lines_list)

    def _invoice_params(self, invoice):
        invoice_obj = {
            "CustomerId": invoice.partner_id.id,
            # "SubCustomerId":"",
            "InvoiceNumber": invoice.name,
            "InvoiceDate": str(invoice.invoice_date) if invoice.invoice_date else '',
            "InvoiceAmount": invoice.amount_total_signed,
            "InvoiceDueDate": str(invoice.invoice_date_due) if invoice.invoice_date_due else '',
            "AmountDue": invoice.amount_residual_signed,
            "Software": "Odoo CRM",
            "NotifyCustomer": False,
            # "Currency": invoice.currency_id.name,
            # "EmailTemplateID": "",
            # "URL": "",
            "TotalTaxAmount": invoice.amount_tax_signed,
            "InvoiceUniqueId": invoice.id,
            # "Description": "Invoice",
            # "CustomerMessage": "",
            "InvoiceMemo": "",
            # "InvoiceShipDate": str(invoice.expected_date.date()),
            # "InvoiceShipVia": "",
            "InvoiceSalesRepId": invoice.user_id.id,
            "PoNum": invoice.ref or "",
            # "InvoiceTermsId": "",
            "InvoiceIsToBeEmailed": 0,
            "InvoiceIsToBePrinted": 0,
            "Items": self._invoice_lines_params(invoice.invoice_line_ids),

            'ShippingAddress': self._get_customer_address(invoice.partner_shipping_id) if invoice.partner_shipping_id else '',
        }
        return invoice_obj

    def _get_customer_address(self, partner):

        name_array = partner.name.split(' ') if partner.name else False
        first_name = name_array[0] if name_array else ''
        if name_array and len(name_array) >= 2:
            last_name = " ".join(name_array[1:])
        else:
            last_name = ""
        Address = {
            "FirstName": first_name,
            "LastName": last_name,
            "CompanyName": partner.name if partner.company_type == "company" else partner.parent_id.name or "",
            "Address1": partner.street or "",
            "Address2": partner.street2 or "",
            "City": partner.city or "",
            "State": partner.state_id.code or "",
            "ZipCode": partner.zip or "",
            "Country": partner.country_id.code or "US"
        }
        return Address

    def _invoice_sync_object(self, invoice):
        sync_object = {
            'securityToken': self._generate_security_json(),
            'invoice': self._invoice_params(invoice)
        }
        return sync_object

    def sync_invoice(self, order):
        inv_params = self._invoice_sync_object(order)
        res = self.client.service.AddInvoice(**inv_params)
        return res

    def get_invoice(self, invoice):
        params = {
            'securityTokenCustomer': self._generate_security_json(),
            'customerId': invoice.partner_id.id,
            'invoiceNumber': invoice.name,
            'invoiceInternalId': invoice.ebiz_internal_id
        }
        return self.client.service.GetInvoice(**params)

    def _update_invoice_params(self, invoice):
        invoice_params = self._invoice_sync_object(invoice)
        invoice_params.update({
                'customerId': invoice.partner_id.id,
                'invoiceNumber': invoice.name,
                'invoiceInternalId': invoice.ebiz_internal_id
            })
        return invoice_params

    def update_invoice(self, invoice):
        invoice_params = self._update_invoice_params(invoice)
        res = self.client.service.UpdateInvoice(**invoice_params)
        return res

    def _transaction_object(self, command = 'sale'):
        obj = {
            'securityToken': self._generate_security_json(),
            'trans':{
                'Command': "",
                'RefNum':"",
                'IsRecurring': "",
                'IgnoreDuplicate': "",
                'CustReceipt': "",
            }
        }
        return obj
    
    def _get_transaction_details(self,sale):
        if sale._name == "sale.order":
            order_id = sale.name
            invoice_id = sale.invoice_ids[0].name if sale.invoice_ids else sale.name
            po = sale.client_order_ref or sale.name
            trans_amount = sale.amount_total
        if sale._name == "account.move":
            order_id = sale.invoice_origin or sale.name
            invoice_id = sale.name
            po = sale.ref or sale.name
            trans_amount = sale.amount_residual

        trans_ids = sale.transaction_ids.filtered(lambda x: x.state == 'draft')
        if trans_ids:
            trans_amount = trans_ids[0].amount

        return {
            'OrderID': order_id,
            'Invoice': invoice_id or "",
            'PONum': po,
            'Description': 'description',
            'Amount': trans_amount,
            # 'Tax': sale.amount_tax,
            'Tax': 0,
            'Shipping': 0,
            'Discount': 0,
            'Subtotal': trans_amount,
            # 'Subtotal': sale.amount_untaxed,
            'AllowPartialAuth': False,
            'Tip': 0,
            'NonTax': True,
            'Duty': 0,
        }

    def _transaction_line(self, line):
        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        tax_ids = line.tax_ids if hasattr(line, 'tax_ids') else line.tax_id
        price_tax = line.price_tax if hasattr(line, 'price_tax') else 0
        return {
            'SKU': line.product_id.id,
            'ProductName': line.product_id.name,
            'Description': line.name,
            'UnitPrice': line.price_unit,
            # 'Taxable': True if tax_ids else False,
            'Taxable': False,
            'TaxAmount': 0,
            # 'TaxAmount': str(price_tax),
            'Qty': str(qty)
        }

    def _transaction_lines(self, lines):
        item_list = []
        for line in lines:
            item_list.append(self._transaction_line(line))
        return {'LineItem':item_list}

    def _get_credit_card_transaction(self, profile, card=None):
        return {
                'InternalCardAuth': False,
                'CardPresent': True,
                'CardNumber': card if card else profile.card_number,
                # 'CardExpiration': profile.card_expiration.strftime('%Y-%m'),
                'CardExpiration': "%s%s"%(profile.card_exp_month, profile.card_exp_year[2:])  ,
                'CardCode': profile.card_code,
                'AvsStreet': profile.avs_street,
                'AvsZip': profile.avs_zip
            }

    def get_transaction_object(self, order, credit_card, profile, command):
        addr = order.partner_id.address_get()
        address_obj = self._get_customer_address_for_transaciotn(order.partner_id)
        obj = {
            "IgnoreDuplicate": False,
            "IsRecurring": False,
            "Details": self._get_transaction_details(order),
            "Software":'Odoo CRM',
            # "ClientIP":'117.102.0.94',
            "ClientIP":'',
            "Command": command,
            "CustReceipt": False,
            "LineItems": self._transaction_lines(order.order_line),
            "CustomerID": order.partner_id.id,
            "CreditCardData": credit_card,
            "AccountHolder": profile['account_holder_name'],
            'BillingAddress': address_obj,
            'ShippingAddress': address_obj
            }
        return obj

    def _get_customer_address_for_transaciotn(self, partner):
        name_array = partner.name.split(' ')
        first_name = name_array[0]
        if len(name_array) >= 2:
            last_name = " ".join(name_array[1:])
        else:
            last_name = ""
        Address = {
            "FirstName": first_name,
            "LastName": last_name,
            "Company": partner.name if partner.company_type == "company" else partner.parent_id.name or "",
            "Street": partner.street or "",
            "Street2": partner.street2 or "",
            "City": partner.city or "",
            "State": partner.state_id.code or "",
            "Zip": partner.zip or "",
            "Country": partner.country_id.code or "US",
        }
        return Address

    def run_transaction(self, order, profile, command='sale'):
        credit_card = self._get_credit_card_transaction(profile)
        transaction_params = self.get_transaction_object(order, credit_card, profile, command)
        params = {
            'securityToken': self._generate_security_json(),
            'tran': transaction_params
        }
        # import pdb
        # pdb.set_trace()
        return self.client.service.runTransaction(**params)

    def get_customer_transaction_object(self, order, profile, command):

        if order.transaction_ids and order.transaction_ids[0].security_code:
            trans_object = {
                "isRecurring":False,
                "IgnoreDuplicate": False,
                "Details": self._get_transaction_details(order),
                "Software":'Odoo CRM',
                "MerchReceipt":True,
                "CustReceipt":False,
                "CustReceiptName":'',
                "CustReceiptEmail":'',
                "ClientIP":'',
                "CardCode": order.transaction_ids[0].security_code,
                "Command": command if profile.token_type == "credit" else "Check",
            }
            for i in order.transaction_ids:
                i.write({
                    'security_code': False
                })
        else:
            trans_object = {
                "isRecurring": False,
                "IgnoreDuplicate": False,
                "Details": self._get_transaction_details(order),
                "Software": 'Odoo CRM',
                "MerchReceipt": True,
                "CustReceipt": False,
                "CustReceiptName": '',
                "CustReceiptEmail": '',
                "ClientIP": '',
                "CardCode": profile.card_code,
                "Command": command if profile.token_type == "credit" else "Check",
            }
            profile.card_code = False
        
        if order._name == 'account.move':
            trans_object['LineItems'] = self._transaction_lines(order.invoice_line_ids)
            trans_object['CustReceipt'] = order.transaction_ids[0].payment_id.ebiz_send_receipt
            trans_object['CustReceiptEmail'] = order.transaction_ids[0].payment_id.ebiz_receipt_emails
            if order.move_type == 'out_refund':
                if profile.token_type == 'credit':
                    trans_object['Command'] = 'Credit'
                else:
                    trans_object['Command'] = 'CheckCredit'
        else:
            trans_object['LineItems'] = self._transaction_lines(order.order_line)

        return trans_object

    def run_customer_transaction(self, order, profile, command='sale'):
        params = {
            "securityToken":self._generate_security_json(),
            # "custNum":order.partner_id.commercial_partner_id.ebizcharge_customer_token,
            "custNum":order.partner_id.ebizcharge_customer_token,
            "paymentMethodID": profile.ebizcharge_profile,
            "tran":self.get_customer_transaction_object(order, profile, command),
        }

        return self.client.service.runCustomerTransaction(**params)

    def run_full_amount_transaction(self, order, profile, command, card):
        credit_card = self._get_credit_card_transaction(profile)
        credit_card['CardNumber'] = card
        transaction_params = self.get_transaction_object_run_trasaction(order, credit_card, profile, command)
        params = {
            "securityToken":self._generate_security_json(),
            "tran": transaction_params,
        }

        return self.client.service.runTransaction(**params)

    def get_transaction_object_run_trasaction(self, order, credit_card, profile, command):
        addr = order.partner_id.address_get()
        address_obj = self._get_customer_address_for_transaciotn(order.partner_id)
        obj = {
            "IgnoreDuplicate": False,
            "IsRecurring": False,
            "Details": self._get_transaction_details(order),
            "Software":'Odoo CRM',
            # "ClientIP":'117.102.0.94',
            "ClientIP":'',
            "Command": command,
            "CustReceipt": False,
            "LineItems": self._transaction_lines(order.invoice_line_ids),
            "CustomerID": order.partner_id.id,
            "CreditCardData": credit_card,
            "AccountHolder": profile['account_holder_name'],
            'BillingAddress': address_obj,
            'ShippingAddress': address_obj
            }
        return obj

    def run_refund_transaction(self, order, profile, command='sale'):
        params = {
            "securityToken":self._generate_security_json(),
            "custNum":order.partner_id.ebizcharge_customer_token,
            "paymentMethodID": profile.ebiz_internal_id,
            "tran":self.get_customer_transaction_object(order, profile, command),
        }
        return self.client.service.runCustomerTransaction(**params)

    def execute_transaction(self, ref_num, kwargs):
        params = {
            'securityToken': self._generate_security_json(),
            'tran':{
                'Command': kwargs['command'],
                'RefNum': ref_num,
                'IsRecurring': False,
                'IgnoreDuplicate': False,
                'CustReceipt': True,
            }
        }
        # if kwargs['command'] in ['credit', 'refund']:
        #     params['tran']['Details'] = {
        #         'Amount': kwargs['amount'],
        #         'NonTax': True
        #     }
        return self.client.service.runTransaction(**params)

    def run_card_validate_transaction(self, transaction, profile):
        params = {
            'securityToken': self._generate_security_json(),
            "tran": {
                "IgnoreDuplicate": False,
                "IsRecurring": False,
                "Software":'Odoo CRM',
                "CustReceipt": False,
                "Command": 'AuthOnly',
                "Details": {
                    'OrderID': "Token",
                    'Invoice': "Token",
                    'PONum': "Token",
                    'Description': 'description',
                    'Amount': 0.05,
                    'Tax': 0,
                    'Shipping': 0,
                    'Discount': 0,
                    'Subtotal': 0.05,
                    'AllowPartialAuth': False,
                    'Tip': 0,
                    'NonTax': True,
                    'Duty': 0
                },
                "CustomerID": transaction.partner_id.id,
                "CreditCardData": self._get_credit_card_transaction(profile),
                "AccountHolder": self.card_account_holder_name,
            }
        }
        
        resp = self.client.service.runTransaction(**params)
        resp_void = self.execute_transaction(resp['ref_num'], **{'command':'void'})
        return resp

    def void_transaction(self, trans, invoice=None):
        ref_num = trans.acquirer_reference
        kwargs = {'command': 'Void'}
        return self.execute_transaction(ref_num, kwargs)

    def capture_transaction(self, trans, invoice=None):
        ref_num = trans.acquirer_reference
        kwargs = {'command': 'Capture'}
        return self.execute_transaction(ref_num, kwargs)

    def return_transaction(self, **kwargs):
        ref_num = kwargs['ref_num']
        kwargs['command'] = "credit"
        return self.execute_transaction(ref_num, kwargs)

    def run_credit_transaction(self, invoice, profile, ref):
        command = "Credit" if profile.token_type == 'credit' else "CheckCredit"
        trans_obj = self.get_customer_transaction_object(invoice, profile, command)
        # trans_obj['RefNum'] = ref
        params = {
            "securityToken": self._generate_security_json(),
            "custNum": invoice.partner_id.ebizcharge_customer_token,
            "paymentMethodID": profile.ebizcharge_profile,
            "tran": trans_obj
        }
        return self.client.service.runCustomerTransaction(**params)

    def run_transaction_without_invoice(self, trans_id):
        payment_token = trans_id.payment_token_id
        command = 'Sale' if payment_token.token_type == 'credit' else 'Check'
        params = {
            "securityToken":self._generate_security_json(),
            "custNum": trans_id.partner_id.ebizcharge_customer_token,
            "paymentMethodID": payment_token.ebizcharge_profile,
            "tran": {
                "isRecurring":False,
                "IgnoreDuplicate": False,
                "Software":'Odoo CRM',
                "MerchReceipt":True,
                "CustReceiptName":'',
                "CustReceiptEmail":'',
                "CustReceipt": False,
                "ClientIP":'',
                "CardCode": payment_token.card_code,
                "Command": command,
                "Details": {
                    'OrderID': "",
                    'Invoice': trans_id.reference ,
                    'PONum': "",
                    'Description': "Customer Credit",
                    'Amount': trans_id.amount,
                    'Tax': 0,
                    'Shipping': 0,
                    'Discount': 0,
                    'Subtotal': trans_id.amount,
                    'AllowPartialAuth': False,
                    'Tip': 0,
                    'NonTax': True,
                    'Duty': 0
                },
            },
        }

        return self.client.service.runCustomerTransaction(**params)