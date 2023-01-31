# -*- coding: utf-8 -*-
from odoo import models, fields, api



class EbizChargeTransaction(models.Model):
    _name = "ebiz.charge.transaction"

    ref_num = fields.Char()
    batch_ref_num = fields.Char()
    batch_num = fields.Char()
    result = fields.Char()
    result_code = fields.Char()
    auth_code = fields.Char()
    auth_amount = fields.Char()
    remaining_balance = fields.Char()
    avs_resultCode = fields.Char()
    avs_result = fields.Char()
    card_code_result_code = fields.Char()
    card_code_result = fields.Char()
    card_level_result_code = fields.Char()
    card_level_result = fields.Char()
    error_code = fields.Char()
    cust_num = fields.Char()
    error = fields.Char()
    acs_url = fields.Char()
    payload = fields.Char()
    vpas_result_code = fields.Char()
    is_duplicate = fields.Char()
    converted_amount = fields.Char()
    converted_amount_currency = fields.Char()
    conversion_rate = fields.Char()
    status = fields.Char()
    status_code = fields.Char()
    profiler_score = fields.Char()
    profiler_response = fields.Char()
    profiler_reason = fields.Char()
    sale_order_id = fields.Many2one('sale.order', "Sale order id")
    invoice_id = fields.Many2one('account.move', "Invoice Id")
    state = fields.Selection([
        ('sale', 'Quotation'),
        ('authonly', 'Quotation'),
        ('captured', 'Quotation Sent'),
        ('voided', 'Credit Void'),
        ('refunded', 'Refund'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='authonly')


    @api.model
    def create_transaction_record(self, resp):
        values = {
            "ref_num":resp["RefNum"],
            "batch_ref_num":resp["BatchRefNum"],
            "batch_num":resp["BatchNum"],
            "result":resp["Result"],
            "result_code":resp["ResultCode"],
            "auth_code":resp["AuthCode"],
            "auth_amount":resp["AuthAmount"],
            "remaining_balance":resp["RemainingBalance"],
            "avs_resultCode":resp["AvsResultCode"],
            "avs_result":resp["AvsResult"],
            "card_code_result_code":resp["CardCodeResultCode"],
            "card_code_result":resp["CardCodeResult"],
            "card_level_result_code":resp["CardLevelResultCode"],
            "card_level_result":resp["CardLevelResult"],
            "error_code":resp["ErrorCode"],
            "cust_num":resp["CustNum"],
            "error":resp["Error"],
            "acs_url":resp["AcsUrl"],
            "payload":resp["Payload"],
            "vpas_result_code":resp["VpasResultCode"],
            "is_duplicate":resp["isDuplicate"],
            "converted_amount":resp["ConvertedAmount"],
            "converted_amount_currency":resp["ConvertedAmountCurrency"],
            "conversion_rate":resp["ConversionRate"],
            "status":resp["Status"],
            "status_code":resp["StatusCode"],
            "profiler_score":resp["ProfilerScore"],
            "profiler_response":resp["ProfilerResponse"],
            "profiler_reason":resp["ProfilerReason"]
        }

        return self.create(values)
