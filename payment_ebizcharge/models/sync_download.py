from  odoo import fields, models,api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
import json
_logger = logging.getLogger(__name__)
from .ebiz_charge import message_wizard


def ref_date(date):
    if not date:
        return date
    rf_date = date.split('-')
    return f"{rf_date[1]}/{rf_date[2]}/{rf_date[0]}"


class EbizPayments(models.TransientModel):
    _name = 'ebiz.payments.lines'

    payment_internal_id = fields.Char('Payment Internal Id')
    partner_id = fields.Many2one('res.partner', 'Customer')
    customer_id = fields.Char('Customer Id')
    invoice_number = fields.Char('Invoice Number')
    invoice_date = fields.Date('Invoice Date')
    invoice_amount = fields.Float('Invoice Total')
    amount_due = fields.Float('Balance')
    currency_id = fields.Many2one('res.currency')
    auth_code = fields.Char('Auth Code')
    ref_num = fields.Char('Reference Number')
    payment_method = fields.Char('Payment Method')
    date_paid = fields.Date('Date Paid')
    paid_amount = fields.Float('Amount Paid')
    type_id = fields.Char('Type')
    payment_type = fields.Char('Payment Type')
    source = fields.Char('Source', default="Odoo")
    is_email_payment = fields.Boolean('Is Email Pay', default = False)
    # payment_date = fields.Date("Payment Date", required="True")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        today = datetime.now()
        end = today + timedelta(days = 1)
        up_dom = []
        start = None
        # domain = self.set_get_date_filter(domain)
        new_domain = []
        for d in domain:
            if d in ["|","&"]: pass
            else: new_domain.append(d)
        domain = new_domain
        for i, do in enumerate(domain):
            if do in ["|","&"]:
                pass
            elif do[0] == 'date_paid':
                start = do[2]
                if do[1] == '=':
                    start, end = do[2], do[2]
                    # break
                if do[1] in ['>=', '>']:
                    start = do[2]
                    if len(domain) > i+1 and domain[i+1][0] == "date_paid":
                        if domain[i+1][1] in ['<=','<']:
                            end = domain[i+1][2]
                            up_dom = domain[0:i]+domain[i+2:]
                            break
                        else:
                            end = str(end.date())
                    else:
                        end = str(end.date())
                if do[1] in ['<=', '<']:
                    end = do[2]

                up_dom = domain[0:i] + domain[i+1:]
                break
                
            else:
                up_dom.append(d)
        if not domain or not start:
            return []

        payments = self.get_payments(start, end)
        payments += self.get_received_email_payments(start, end)
        self.env['ebiz.payments.lines'].search([]).unlink()
        self.create(payments)
        res = super(EbizPayments, self).search_read(up_dom, fields, offset, limit, order)
        return res

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     today = datetime.now()
    #     end = today + timedelta(days = 1)
    #     up_dom = []
    #     for d in domain:
    #         if d[0] in ['date_filter']:
    #             start = self.env['res.config.settings'].get_start_date(*d[2].split('-'))
    #             dom = ['&',('filter_date','>=', start),('filter_date','<=', end.date())]
    #             up_dom+=dom
    #         else:
    #             up_dom.append(d)
    #     i = 0 
    #     new_up = []
    #     date_domain = []
    #     try:
    #         while i < len(up_dom):
    #             if up_dom[i][0] == 'date_filter':
    #                 if i>=1 and up_dom[i-1] in ['&', '|']:
    #                     date_domain+=[]
    #                     if up_dom[i+1][0] == 'date_filter':
    #                         date_domain += up_dom[i-1:i+2]
    #                         up_dom = up_dom[:i-1] +up_dom[i+2:]
    #                         i=i-1
    #                     else:
    #                         date_domain += up_dom[i-1:i+1]
    #                         up_dom = up_dom[:i-1] +up_dom[i+1:]
    #                         i=i-1
    #             else:
    #                 date_domain = up_dom[i]
    #                 i+=1
    #     except:
    #         pass
    #     res = super(EbizPayments, self).search_read(up_dom, fields, offset, limit, order)
    #     return res

    def set_get_date_filter(self, domain):
        date_domain = []
        up_dom = []
        for d in domain:
            if d[0] in ['filter_date', 'date_filter']:
                date_domain.append(d)
            else:
                up_dom.append(d)

        filters = self.env['ir.config_parameter'].sudo().get_param('payment_ebizcharge.ebiz_payment_lines')
        filters = json.loads(filters) if filters else []

        if date_domain == filters:
            return up_dom
        else: 
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.ebiz_payment_lines', json.dumps(date_domain))
            return domain        
    
    def get_payments(self, start, end):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        params = {
            'securityToken': ebiz._generate_security_json(),
            "fromDateTime": str(start)+"T00:00:00",
            "toDateTime": str(end)+"T23:59:59",
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.GetPayments(**params)
        payment_lines = []

        if not payments:
            return payment_lines
        for payment in payments:
            try:
                currency_id = self.env['res.partner'].browse(int(payment['CustomerId'])).property_product_pricelist.currency_id.id
                customer_id = int(payment['CustomerId'])
            except:
                currency_id = 2
                customer_id = None

            try:
                self.env['res.partner'].browse(customer_id).name
            except:
                continue

            payment_line = {
                "payment_type": payment['PaymentType'],
                "payment_internal_id": payment['PaymentInternalId'],
                "customer_id": payment['CustomerId'],
                "partner_id": customer_id,
                "invoice_number": payment['InvoiceNumber'],
                # "invoice_internal_id": payment['InvoiceInternalId'],
                "invoice_date": payment['InvoiceDate'].split('T')[0] if payment['InvoiceDate'] else payment['InvoiceDate'],
                # "invoice_due_date": ref_date(payment['InvoiceDueDate']),
                # "po_num": payment['PoNum'],
                # "so_num": payment[''],
                "invoice_amount": float(payment['InvoiceAmount'] or "0"),
                "currency_id": currency_id,
                "source": payment['PaymentSourceId'] or "N/A",
                "amount_due": payment['AmountDue'],
                # "currency": payment[''],
                "auth_code": payment['AuthCode'],
                "ref_num": payment['RefNum'],
                "payment_method": f"{payment['PaymentMethod']} ending in {payment['Last4']}",
                "date_paid": payment['DatePaid'].split('T')[0],
                "paid_amount": float(payment['PaidAmount'] or "0"),
                # "payment_date": payment['DatePaid'].split('T')[0],
                "type_id": payment['TypeId'],
            }
            # payment_lines.append([0,0, payment_line])
            payment_lines.append(payment_line)
        return payment_lines

    def mark_as_applied(self):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
        message_lines = []
        success = 0
        failed = 0
        total = len(self)
        try:
            for item in self:
                message_record = {
                    'customer_name':item.partner_id.name,
                    'customer_id': item.partner_id.id,
                    'invoice_no': item.invoice_number,
                    'status': 'Success'
                }
                invoice = self.env['account.move'].search([('name','=',item.invoice_number)])
                credit = self.env['account.payment'].search([('name','=',item.invoice_number)])
                try:
                    if invoice:
                        invoice.ebiz_create_payment_line(item.paid_amount)
                        if not item.is_email_payment:
                            resp = ebiz.client.service.MarkPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': item.payment_internal_id,
                                'invoiceNumber': item.invoice_number
                                })
                        else:
                            resp = ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                                'securityToken': ebiz._generate_security_json(),
                                'paymentInternalId': item.payment_internal_id,

                            })
                    if credit:
                        resp = ebiz.client.service.MarkPaymentAsApplied(**{
                            'securityToken': ebiz._generate_security_json(),
                            'paymentInternalId': item.payment_internal_id,
                            'invoiceNumber': item.invoice_number
                        })
                        credit.action_draft()
                        credit.cancel()
                    success+=1
                except Exception as e:
                    _logger.exception(e)
                    failed +=1
                    message_record['status'] = 'Failed'

                message_lines.append([0, 0, message_record])
            self.env['ir.config_parameter'].sudo().set_param('payment_ebizcharge.ebiz_payment_lines', json.dumps([]))
            wizard = self.env['download.pyament.message'].create({'name':'Download', 'lines_ids':message_lines,
            'succeeded': success, 'failed': failed, 'total': total})
            action = self.env.ref('payment_ebizcharge.wizard_ebiz_download_message_action').read()[0]
            action['context'] = self._context
            action['res_id'] = wizard.id
            return action
            
        except Exception as e:
            _logger.exception(e)
            raise ValidationError(str(e))
        return message_wizard('Payment has been successfully applied!')

    def get_received_email_payments(self,  start, end):
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        params = {
            'securityToken': ebiz._generate_security_json(),
            "fromPaymentRequestDateTime": str(start)+"T00:00:00",
            "toPaymentRequestDateTime": str(end)+"T23:59:59",
            "filters": {'SearchFilter': []},
            "limit": 1000,
            "start": 0,
        }
        payments = ebiz.client.service.SearchEbizWebFormReceivedPayments(**params)
        payment_lines = []



        if not payments:
            return payment_lines

        for payment in payments:
            if payment['InvoiceNumber'] in ['PM', "Token"]: continue
            try:
                currency_id = self.env['res.partner'].browse(int(payment['CustomerId'])).property_product_pricelist.currency_id.id
                customer_id = int(payment['CustomerId'])
            except:
                currency_id = 2
                customer_id = None

            try:
                self.env['res.partner'].browse(customer_id).name
            except:
                continue
            payment_line = {
                "payment_type": payment['PaymentType'],
                "payment_internal_id": payment['PaymentInternalId'],
                "customer_id": payment['CustomerId'],
                "partner_id": customer_id,
                "invoice_number": payment['InvoiceNumber'],
                # "invoice_internal_id": payment['InvoiceInternalId'],
                "invoice_date": payment['InvoiceDate'].split('T')[0] if payment['InvoiceDate'] else payment['InvoiceDate'],
                # "invoice_due_date": ref_date(payment['InvoiceDueDate']),
                # "po_num": payment['PoNum'],
                "invoice_amount": float(payment['InvoiceAmount'] or "0"),
                "currency_id": currency_id,
                "source": payment['PaymentSourceId'] or "N/A",
                "amount_due": payment['AmountDue'],
                # "currency": payment[''],
                "auth_code": payment['AuthCode'],
                "ref_num": payment['RefNum'],
                "payment_method": f"{payment['PaymentMethod']} ending in {payment['Last4']}",
                "date_paid": payment['DatePaid'].split('T')[0],
                "paid_amount": float(payment['PaidAmount'] or "0"),
                "type_id": payment['TypeId'],
                # "payment_date": payment['DatePaid'].split('T')[0],
                "is_email_payment": True,
            }
            # payment_lines.append([0,0, payment_line])
            payment_lines.append(payment_line)
        return payment_lines


    @api.model
    def fields_get(self, fields=None):
        hide = ['invoice_number','amount_due']
        res = super(EbizPayments, self).fields_get()
        for field in hide:
            res[field]['selectable'] = False
        return res

class BatchProcessMessage(models.TransientModel):
    _name = "download.pyament.message"

    name = fields.Char("Name")
    failed = fields.Integer("Failed")
    succeeded = fields.Integer("Succeeded")
    total = fields.Integer("Total")
    lines_ids = fields.One2many('download.pyament.message.line', 'message_id')


class BatchProcessMessageLines(models.TransientModel):
    _name = "download.pyament.message.line"

    customer_id = fields.Char('Customer Id')
    customer_name = fields.Char('Customer Name')
    invoice_no = fields.Char('Number')
    status = fields.Char('Status')
    message_id = fields.Many2one('download.pyament.message')
