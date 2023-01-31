from  odoo import fields, models,api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class DownloadEbizPayment(models.TransientModel):
    _name = 'ebiz.pending.payment'

    payment_lines = fields.One2many('ebiz.pending.payment.lines', 'wizard_id')



class EbizPaymentLines(models.TransientModel):
    _name = 'ebiz.pending.payment.lines'

    wizard_id = fields.Many2one('ebiz.pending.payment')
    payment_internal_id = fields.Char('Payment Internal Id')
    customer_id = fields.Char('Customer ID')
    invoice_number = fields.Char('Number')
    invoice_internal_id = fields.Char('Invoice Internal Id')
    invoice_date = fields.Char('Invoice Date')
    invoice_due_date = fields.Char('Invoice Due Date')
    po_num = fields.Char('Po Num')
    so_num = fields.Char('So Num')
    currency_id = fields.Many2one('res.currency', string='Company Currency')
    invoice_amount = fields.Float('Invoice Total')
    email_amount = fields.Char('Requested Amount')
    amount_due = fields.Float('Requested Amount')
    currency = fields.Char('Currency')
    auth_code = fields.Char('Auth Code')
    ref_num = fields.Char('Ref Num')
    payment_method = fields.Char('Payment Method')
    date_paid = fields.Datetime('Request Date & Time')
    paid_amount = fields.Float('Amount Paid')
    type_id = fields.Char('Type Id')
    payment_type = fields.Char('Payment Type')
    email_id = fields.Char('Email')
    # PaymentType
    # MerchantId
    # PaymentInternalId
    # CustomerId
    # SubCustomerId
    # DivisionId
    # InvoiceNumber
    # InvoiceInternalId
    # InvoiceDate
    # InvoiceDueDate
    # PoNum
    # SoNum
    # InvoiceAmount
    # AmountDue
    # Currency
    # AuthCode
    # RefNum
    # Last4
    # PaymentMethod
    # DatePaid
    # PaidAmount
    # TypeId
    # PaymentSourceId
    # PaymentType
    # TransactionLookupKey
    # ExternalTxnId


