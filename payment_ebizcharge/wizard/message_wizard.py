from odoo import fields, models,api, _
from datetime import datetime, timedelta
from ..models.ebiz_charge import message_wizard


class CustomMessageWizard(models.TransientModel):
    _name = 'message.wizard'

    def get_default(self):
        if self.env.context.get("message",False):
            return self.env.context.get("message")
        return False

    text = fields.Text('Message', readonly=True, default=get_default)


class WizardDeleteToken(models.TransientModel):
    _name = 'wizard.token.delete.confirmation'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        self.env[self.record_model].browse(self.record_id).unlink()
        return message_wizard('The payment method has been deleted successfully!')


class WizardDeleteEmailPay(models.TransientModel):
    _name = 'wizard.delete.email.pay'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        values = self.env.context.get('kwargs_values')
        pending_received_msg = self.env.context.get('pending_recieved')

        success = 0

        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        for invoice in values:
            odoo_invoice = self.env['account.move'].search([('id', '=', invoice['invoice_id'])])

            if pending_received_msg == 'Pending Requests':
                form_url = ebiz.client.service.DeleteEbizWebFormPayment(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': odoo_invoice.payment_internal_id,
                })

                if form_url.Status == 'Success':
                    odoo_invoice.ebiz_invoice_status = 'delete'
                    success += 1
                    pending_payments = self.env['payment.request.bulk.email'].search([])
                    for payment in pending_payments:
                        if payment.transaction_history_line_pending:
                            for pending in payment.transaction_history_line_pending:
                                if pending.id == invoice['invoice_id']:
                                    payment.transaction_history_line_pending = [[2, invoice['invoice_id']]]
                                    dict2 = {
                                        'name': invoice['name'],
                                        'customer_name': odoo_invoice.partner_id.id,
                                        'customer_id': str(odoo_invoice.partner_id.id),
                                        'email_id': odoo_invoice.partner_id.email,
                                        'invoice_id': odoo_invoice.id,
                                        'invoice_date': odoo_invoice.date,
                                        'sales_person': self.env.user.id,
                                        'amount': odoo_invoice.amount_total,
                                        "currency_id": odoo_invoice.currency_id.id,
                                        'amount_due': odoo_invoice.amount_residual_signed,
                                        'tax': odoo_invoice.amount_untaxed_signed,
                                        'invoice_due_date': odoo_invoice.invoice_date_due,
                                        'sync_transaction_id': payment.id,
                                    }
                                    new_sync_invoice = self.env['sync.request.payments.bulk'].create(dict2)
                                    payment.transaction_history_line = [[4, new_sync_invoice.id]]

            elif pending_received_msg == 'Received Email Payments':
                form_url = ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': odoo_invoice.payment_internal_id,
                })

                if form_url.Status == 'Success':
                    odoo_invoice.email_recieved_payments = False
                    odoo_invoice.ebiz_invoice_status = False
                    success += 1
                    received_payments = self.env['payment.request.bulk.email'].search([])
                    for payment in received_payments:
                        if payment.transaction_history_line_received:
                            for pending in payment.transaction_history_line_received:
                                if pending.id == invoice['id']:
                                    payment.transaction_history_line_received = [[2, invoice['id']]]
                                    dict2 = {
                                        'name': invoice['name'],
                                        'customer_name': odoo_invoice.partner_id.id,
                                        'customer_id': str(odoo_invoice.partner_id.id),
                                        'email_id': odoo_invoice.partner_id.email,
                                        'invoice_id': odoo_invoice.id,
                                        'invoice_date': odoo_invoice.date,
                                        'sales_person': self.env.user.id,
                                        'amount': odoo_invoice.amount_total,
                                        "currency_id": odoo_invoice.currency_id.id,
                                        'amount_due': odoo_invoice.amount_residual_signed,
                                        'tax': odoo_invoice.amount_untaxed_signed,
                                        'invoice_due_date': odoo_invoice.invoice_date_due,
                                        'sync_transaction_id': payment.id,
                                    }
                                    new_sync_invoice = self.env['sync.request.payments.bulk'].create(dict2)
                                    payment.transaction_history_line = [[4, new_sync_invoice.id]]

            odoo_invoice.save_payment_link = False

        if pending_received_msg == 'Pending Requests':
            return message_wizard(f'{success} request(s)  were successfully removed from {pending_received_msg}!')
        elif pending_received_msg == 'Received Email Payments':
            return message_wizard(f'{success} payment(s)  were successfully removed from {pending_received_msg}!')


class WizardDeletePaymentMethods(models.TransientModel):
    _name = 'wizard.delete.payment.methods'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        values = self.env.context.get('kwargs_values')
        pending_received_msg = self.env.context.get('pending_recieved')
        success = 0

        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        for record in values:
            if pending_received_msg == 'Pending Requests':
                form_url = ebiz.client.service.DeleteEbizWebFormPayment(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': record['payment_internal_id'],
                })
                success += 1
                pending_methods = self.env['payment.method.ui'].search([])
                for method in pending_methods:
                    if method.transaction_history_line_pending:
                        for pending in method.transaction_history_line_pending:
                            try:
                                if pending.id == record['id']:
                                    method.transaction_history_line_pending = [[2, record['id']]]
                            except Exception:
                                pass
            elif pending_received_msg == 'Added Payment Methods':
                form_url = ebiz.client.service.MarkEbizWebFormPaymentAsApplied(**{
                    'securityToken': ebiz._generate_security_json(),
                    'paymentInternalId': record['payment_internal_id'],
                })
                success += 1
                received_methods = self.env['payment.method.ui'].search([])
                for method in received_methods:
                    if method.transaction_history_line_received:
                        for pending in method.transaction_history_line_received:
                            if pending.id == record['id']:
                                method.transaction_history_line_received = [[2, record['id']]]

        else:
            if pending_received_msg == 'Pending Requests':
                return message_wizard(f'{success} request(s) were successfully removed from Pending Requests!')
            elif pending_received_msg == 'Added Payment Methods':
                return message_wizard( f'{success} payment method(s) were successfully removed from Added Payment Methods!')


class WizardDeleteDownloadLogs(models.TransientModel):
    _name = 'wizard.delete.logs.download'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        values = self.env.context.get('kwargs_values')
        success = 0
        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        for record in values:
            record_check = self.env['sync.logs'].search(
                [('invoice_number', '=', record['invoice_number']), ('ref_num', '=', record['ref_num'])])
            if record_check:
                record_check.unlink()
                success += 1

        else:
            return message_wizard(f'{success} payment(s) were successfully cleared from the Log!')


class WizardDeleteUploadLogs(models.TransientModel):
    _name = 'wizard.delete.upload.logs'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        values = self.env.context.get('list_of_records')
        model_type = self.env.context.get('model')
        success = 0

        for record in values:
            record_to_dell = self.env[model_type].search([('id', '=', record)])
            if record_to_dell:
                record_to_dell.unlink()
                success += 1

        else:
            return message_wizard(f'{success} {self.record_model}(s) were successfully cleared from the Log!')


class WizardDeleteInactiveCustomer(models.TransientModel):
    _name = 'wizard.inactive.customers'

    record_id = fields.Integer('Record Id')
    record_model = fields.Char('Record Model')
    text = fields.Text('Message', readonly=True)

    def delete_record(self):
        values = self.env.context.get('kwargs_values')
        values_of_records = self.env.context.get('list_of_records')
        success = 0

        for record in values_of_records:
            dell_rec = self.env['list.of.customers'].search([('id', '=', record)])
            if dell_rec:
                dell_rec.unlink()

        for record in values:
            ebiz_customer = self.env['res.partner'].search([('id', '=', record)])
            if ebiz_customer:
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                templates = ebiz.client.service.MarkCustomerAsInactive(**{
                    'securityToken': ebiz._generate_security_json(),
                    'customerInternalId': ebiz_customer.ebiz_internal_id,
                })
                ebiz_customer.active = False
                success += 1

        else:
            return message_wizard(f'{success} customer(s) were successfully deactivated in Odoo and EBizCharge Hub!')


class WizardRecievedEmailPay(models.TransientModel):
    _name = 'wizard.recieve.email.pay'

    record_id = fields.Integer('Record Id')
    odoo_invoice = fields.Many2one('account.move', 'Odoo Invoice')
    text = fields.Text('Message', readonly=True)

    def apply_record(self):
        import ast
        self.odoo_invoice.recieved_apply_email_after_confirmation(ast.literal_eval(f"{self.env.context.get('invoice')}"))


class WizardReceivedEmailPayPaymentLink(models.TransientModel):
    _name = 'wizard.receive.email.payment.link'

    record_id = fields.Integer('Record Id')
    odoo_invoice = fields.Many2one('account.move', 'Odoo Invoice')
    text = fields.Text('Message', readonly=True)

    def send_email(self):
        odoo_invoice = self.env['account.move'].search([('id', '=', self.record_id)])

        ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

        ebiz.client.service.DeleteEbizWebFormPayment(**{
            'securityToken': ebiz._generate_security_json(),
            'paymentInternalId': odoo_invoice.payment_internal_id,
        })

        odoo_invoice.save_payment_link = False

        return {'type': 'ir.actions.act_window',
                'name': _('Email Pay Request'),
                'res_model': 'email.invoice',
                'target': 'new',
                # 'view_id': self.env.ref('payment_ebizcharge.send_email_invoice_wizard').id,
                'view_mode': 'form',
                'view_type': 'form',
                'context': {
                    'default_contacts_to': [[6, 0, [odoo_invoice.partner_id.id]]],
                    'default_record_id': odoo_invoice.id,
                    'default_currency_id': odoo_invoice.currency_id.id,
                    'default_amount': odoo_invoice.amount_residual if odoo_invoice.amount_residual else odoo_invoice.amount_total,
                    'default_model_name': 'account.move',
                    'default_email_customer': str(odoo_invoice.partner_id.email),
                    'selection_check': 1,
                },
                }


class WizardCreditNoteValidation(models.TransientModel):
    _name = 'wizard.credit.note.validate'

    invoice_id = fields.Many2one('account.move')
    text = fields.Text('Message', readonly=True)

    def proceed(self):
        context = dict(self._context)
        context['bypass_credit_note_restriction'] = True

        return self.invoice_id.with_context(context).action_reverse()


class EmailPayMessage(models.TransientModel):
    _name = 'wizard.email.pay.message'

    name = fields.Char("Customer")
    success_count = fields.Integer("Success Count")
    failed_count = fields.Integer("Failed Count")
    total = fields.Integer("Total")
    lines_ids = fields.One2many('wizard.email.pay.message.line', 'message_id')


class EmailPayMessageLine(models.TransientModel):
    _name = "wizard.email.pay.message.line"

    message_id = fields.Many2one('wizard.email.pay.message')
    status = fields.Char("Status")
    customer_id = fields.Integer("Customer ID")
    number = fields.Many2one('account.move', "Number")
    customer_name = fields.Many2one('res.partner', string="Customer")


class MultiPaymentMsg(models.TransientModel):
    _name = 'wizard.multi.payment.message'

    name = fields.Char("Customer")
    success_count = fields.Integer("Success Count")
    failed_count = fields.Integer("Failed Count")
    total = fields.Integer("Total")
    lines_ids = fields.One2many('wizard.multi.payment.message.line', 'message_id')


class MultiPaymentMsgLine(models.TransientModel):
    _name = "wizard.multi.payment.message.line"

    message_id = fields.Many2one('wizard.multi.payment.message')
    status = fields.Char("Status")
    customer_id = fields.Integer("Customer ID")
    email_address = fields.Char("Email")
    customer_name = fields.Many2one('res.partner', string="Customer")


class MultiTransactionsMsg(models.TransientModel):
    _name = 'wizard.transaction.history.message'

    name = fields.Char("Customer")
    success_count = fields.Integer("Success Count")
    failed_count = fields.Integer("Failed Count")
    lines_ids = fields.One2many('wizard.transaction.history.message.line', 'message_id')


class MultiTransactionsLine(models.TransientModel):
    _name = "wizard.transaction.history.message.line"

    message_id = fields.Many2one('wizard.transaction.history.message')
    status = fields.Char("Status")
    customer_id = fields.Char("Customer Id")
    ref_num = fields.Char("Reference Number")
    customer_name = fields.Char("Customer")


