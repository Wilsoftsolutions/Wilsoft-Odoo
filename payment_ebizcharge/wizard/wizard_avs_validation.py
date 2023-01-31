from odoo import fields, models,api
import json
from odoo import _
from ..models.ebiz_charge import message_wizard
import ast

class WizarcTransactionValidation(models.TransientModel):
    _name = 'wizard.ebiz.transaction.validation'
    """
    Kuldeeps implementation
    Wizard for showing avs validation reposne
    """
    transaction_id = fields.Many2one('payment.transaction')
    wizard_prcoess_id = fields.Many2one('wizard.order.process.transaction')
    transaction_result = fields.Html('Html field')
    address = fields.Char('Address', default="Match")
    zip_code = fields.Char('Zip/Postal Code', default="Match")
    card_code = fields.Char('CVV2/CVC', default="Match")
    check_avs_match = fields.Boolean()
    is_card_denied = fields.Boolean("Is Card Denied")
    denied_message = fields.Char("Denied Message")
    payment_id = fields.Many2one("account.payment")
    full_amount_avs = fields.Boolean("Full Amount AVS")    

    def void_transaction(self):
        """
        Kuldeeps implementation
        return void Transaction Wizard
        """
        if self.payment_id and self.payment_id.move_id:
            recipets_exists = self.env['account.move.receipts'].search([])
            if recipets_exists:
                if int(self.env['account.move.receipts'].search([])[-1].invoice_id) in self.env['account.move'].search([('name', '=', self.payment_id.ref)]).ids:
                    recipets_exists[-1].unlink()

        if self.transaction_id:

            if self.env.context.get('customer_token_to_dell') and self.env.context.get('payment_method_id_to_dell'):
                ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
                try:
                    resp = ebiz.client.service.DeleteCustomerPaymentMethodProfile(**{
                        'securityToken': ebiz._generate_security_json(),
                        'customerToken': self.env.context.get('customer_token_to_dell'),
                        'paymentMethodId': self.env.context.get('payment_method_id_to_dell'),
                    })
                except:
                    pass

            return self.transaction_id.s2s_void_transaction()

        if self.payment_id:
            if self.env.context.get('my_full_amount'):
                token_id = self.payment_id.create_credit_card_payment_methode().id
                self.payment_id.payment_token_id = token_id

            return self.payment_id.cancel()
        return True

    def procceed_with_transaction(self):
        """
        Kuldeeps implementation
        Proceed With transaction 
        """
        if self.wizard_prcoess_id.card_id:
            return True
        elif self.payment_id:
            # if the avs validation ran through 0.05 
            if not self.transaction_id:
                if self.env.context.get('my_full_amount'):
                    self.payment_id.with_context({'avs_bypass': True, 'bypass_card_creation': True, 'payment_data': self._context['payment_data']}).action_post()
                elif self.env.context.get('ebiz_charge_profile'):
                    self.payment_id.with_context({'avs_bypass': True, 'get_customer_profile': self.env.context.get('ebiz_charge_profile'), 'payment_data': self._context['payment_data']}).action_post()
                else:
                    self.payment_id.with_context({'avs_bypass': True, 'payment_data': self._context['payment_data']}).action_post()
                return True
            # if we ran transactoin with deposite command we need to set the state to done to bypass capture
            if self.payment_id.transaction_command == "Sale":
                self.transaction_id._set_transaction_done()
                self.payment_id.with_context({'avs_bypass': True, 'payment_data': self._context['payment_data']}).action_post()
        
        else:
            self.wizard_prcoess_id.prcoess_new_card_transaction()
            return message_wizard('Successful!')

    def update_and_retry(self):
        """
        Kuldeeps implementation
        Proceed With transaction 
        """
        if self.wizard_prcoess_id:
            self.wizard_prcoess_id.write({
                "card_id": None,
                "card_card_number": "",
                "card_exp_year": "",
                "card_exp_month": "",
                "card_card_code": "",
                })
            action = self.env.ref('payment_ebizcharge.action_process_ebiz_transaction').read()[0]
            action['res_id'] = self.wizard_prcoess_id.id
            return action 
        else:
            self.payment_id.write({
                "card_id": None,
                "card_card_number": "",
                "card_exp_year": "",
                "card_exp_month": "",
                "card_card_code": "",
                })
            context = dict(self.env.context)
            context['active_model'] = 'account.move'
            return {
                'name': _('Register Payment'),
                'res_model': 'account.payment',
                'res_id': self.payment_id.id,
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_account_payment_invoice_form').id,
                'context': context,
                'target': 'new',
                'type': 'ir.actions.act_window',
            }

            return

    def show_void_wizard(self):
        """
        Kuldeeps implementation
        function for void transaction wizard
        """
        wiz = self.env['wizard.ebiz.transaction.void'].create({
            'transaction_id': self.transaction_id.id,
            'wizard_prcoess_id': self.wizard_prcoess_id.id})
        action = self.env.ref('payment_ebizcharge.action_ebiz_transaction_void_form').read()[0]
        action['res_id'] = wiz.id
        return action 