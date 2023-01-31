
from odoo import models, api, fields
import json
from odoo.exceptions import UserError, ValidationError, Warning
from ..models.ebiz_charge import message_wizard


class EmailReceipt(models.TransientModel):

    _name = 'wizard.email.receipts'

    contacts_to = fields.Many2many('res.partner', string='Customer')
    select_template = fields.Many2one('email.receipt', string='Select Template', required=True)
    email_subject = fields.Char(string='Subject', related='select_template.receipt_subject')
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('')
    email_transection_id = fields.Char(string='RefNum')

    multiple_ref_num = fields.Many2many('account.move.receipts', string='Select Transaction',)

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

            # if not saleorder.partner_id.email:
            #     raise UserError(f'"{saleorder.partner_id.name}" does not contain Email Address!')
            
            for ref_no in self.multiple_ref_num:
                if '@' in self.email_customer and '.' in self.email_customer:
                    form_url = ebiz.client.service.EmailReceipt(**{
                        'securityToken': ebiz._generate_security_json(),
                        # 'transactionRefNum': self.email_transection_id,
                        'transactionRefNum': ref_no['ref_nums'],
                        'receiptRefNum': self.select_template.receipt_id,
                        'receiptName': self.select_template.name,
                        # 'emailAddress': self.contacts_to.email,
                        'emailAddress': self.email_customer,
                    })
                else:
                    raise UserError('You might have entered wrong email address!')

            if form_url.Status == 'Success':
                return message_wizard('The invoice receipt has been sent successfully!')
            elif form_url.Status == 'Failed':
                raise UserError('You might have entered wrong email address!')

        except Exception as e:
            raise ValidationError(e)
    
    
class EmailReceiptBulk(models.TransientModel):

    _name = 'wizard.email.receipts.bulk'

    contacts_to = fields.Many2many('res.partner', string='Customer')
    select_template = fields.Many2one('email.receipt', string='Select Template')
    email_subject = fields.Char(string='Subject', related='select_template.receipt_subject')
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('', related='contacts_to.email', readonly=True)
    email_transection_id = fields.Char(string='RefNum')

    def send_email(self):
        try:

            resp_lines = []
            success = 0
            failed = 0

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            filter_record = self.env['transaction.history'].browse(self._context.get('transaction_ids'))

            for record in filter_record:
                resp_line = {}

                resp_line.update({
                    'customer_name': record['account_holder'],
                    'customer_id': record['customer_id'],
                    'ref_num': record['ref_no'],
                })

                if record['email_id']:
                    if '@' in record['email_id'] and '.' in record['email_id']:
                        form_url = ebiz.client.service.EmailReceipt(**{
                            'securityToken': ebiz._generate_security_json(),
                            'transactionRefNum': record['ref_no'],
                            'receiptRefNum': self.select_template.receipt_id,
                            'receiptName': self.select_template.name,
                            'emailAddress': record['email_id'],
                            # 'emailAddress': 'niazbscs1@gmail.com',
                        })

                        if form_url.Status == 'Success':
                            resp_line['status'] = 'Success'
                            success += 1
                        elif form_url.Status == 'Failed':
                            resp_line['status'] = 'Failed!'
                            failed += 1
                    else:
                        resp_line['status'] = 'Wrong Email Address!'
                        failed += 1

                else:
                    resp_line['status'] = 'Email ID Not Found!'
                    failed += 1

                resp_lines.append([0, 0, resp_line])
            else:

                wizard = self.env['wizard.transaction.history.message'].create({'name': 'Message', 'lines_ids': resp_lines,
                                                                                'success_count': success,
                                                                                'failed_count': failed, })
                # action = self.env.ref('payment_ebizcharge.wizard_transaction_message_action').read()[0]
                # action['context'] = self._context
                # action['res_id'] = wizard.id
                # return action
                return {'type': 'ir.actions.act_window',
                        'name': 'Email Receipt',
                        'res_model': 'wizard.transaction.history.message',
                        'target': 'new',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_id': wizard.id,
                        'context': self._context
                        }

        except Exception as e:
            raise ValidationError(e)