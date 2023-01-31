from odoo import fields, models,api
import json
from ..models.ebiz_charge import message_wizard


class WizarcTransactionValidation(models.TransientModel):
    _name = 'wizard.add.card.validation'
    """
    Kuldeeps implementation
    Wizard for showing avs validation reposne
    """
    wizard_prcoess_id = fields.Many2one('wizard.add.new.card')
    address = fields.Char('Address', default="Match")
    zip_code = fields.Char('Zip/Postal Code', default="Match")
    card_code = fields.Char('CVV2/CVC', default="Match")
    check_avs_match = fields.Boolean(compute="_compute_avs_validation_resp")
    is_card_denied = fields.Boolean("Is Card Denied")
    denied_message = fields.Char("Denied Message")

    def _compute_avs_validation_resp(self):
        self.check_avs_match = (self.card_code.strip() == 'Match') & (self.address.strip() == 'Match') & (self.zip_code.strip() == 'Match')

    def save_card_anyway(self):
        """
        Kuldeeps implementation
        Proceed With transaction 
        """
        return self.wizard_prcoess_id.create_credit_card_payment_method_default_msg()
        return message_wizard('Card has been successfully saved!')

    def update_and_retry(self):
        """
        Kuldeeps implementation
        Proceed With transaction 
        """

        action = self.env.ref('payment_ebizcharge.action_wizard_add_new_card').read()[0]
        action['res_id'] = self.wizard_prcoess_id.id
        self.wizard_prcoess_id.write({
            "card_card_number":"",
            "card_exp_year":"",
            "card_exp_month":"",
            "card_card_code":"",
            })
        return action
            

    def show_void_wizard(self):
        """
        Kuldeeps implementation
        function for void transaction wizard
        """
        wiz = self.env['wizard.ebiz.transaction.void'].create({
            'sale_order_id': self.sale_order_id.id,
            'wizard_prcoess_id': self.wizard_prcoess_id.id,
            'invoice_id': self.invoice_id.id})
        action = self.env.ref('payment_ebizcharge.action_ebiz_transaction_void_form').read()[0]
        action['res_id'] = wiz.id
        return action 
