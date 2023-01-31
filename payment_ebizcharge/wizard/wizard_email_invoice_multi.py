
from odoo import models, api, fields
import json
from odoo.exceptions import UserError, ValidationError, Warning
from ..models.ebiz_charge import message_wizard


class EmailReceipt(models.TransientModel):

    _name = 'wizard.email.multi.receipts'

    contacts_to = fields.Many2many('res.partner', string='Customer')
    select_template = fields.Many2one('email.receipt', string='Select Template')
    email_subject = fields.Char(string='Subject')
    record_id = fields.Char(string='Record ID')
    model_name = fields.Char(string='Model Name')
    email_customer = fields.Char('', related='contacts_to.email', readonly=True)
    email_transection_id = fields.Char(string='RefNum')

    def send_email(self):
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))

            if not saleorder.partner_id.email:
                raise UserError(f'"{saleorder.partner_id.name}" does not contain Email Address!')

            form_url = ebiz.client.service.EmailReceipt(**{
                'securityToken': ebiz._generate_security_json(),
                'transactionRefNum': self.email_transection_id,
                'receiptRefNum': self.select_template.receipt_id,
                'receiptName': self.select_template.name,
                'emailAddress': self.contacts_to.email,
            })

            if form_url.Status == 'Success':
                return message_wizard('The invoice receipt has been sent successfully!')
            elif form_url.Status == 'Failed':
                raise UserError('Operation Denied!')

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
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            filter_record = self.env['sync.history.transaction'].search([('check_box', '=', True)])

            # saleorder = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_id'))
            list_of_sucess = 'Ref Num           :   Status\n\n'

            for record in filter_record:
                ref_no = record['ref_no']
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
                            list_of_sucess += f'{ref_no}     :   Success\n'
                        elif form_url.Status == 'Failed':
                            list_of_sucess += f'{ref_no}     :   Failed!\n'
                    else:
                        list_of_sucess += f'{ref_no}     :   Wrong Email Address\n'

                else:
                    list_of_sucess += f'{ref_no}     :   Email ID Not Found!\n'
            else:
                return message_wizard(list_of_sucess)

        except Exception as e:
            raise ValidationError(e)
