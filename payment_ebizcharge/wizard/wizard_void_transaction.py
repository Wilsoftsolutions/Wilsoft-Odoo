from odoo import fields, models,api
import json

class WizarcTransactionValidation(models.TransientModel):
    _name = 'wizard.ebiz.transaction.void'

    transaction_id = fields.Many2one('payment.transaction')
    wizard_prcoess_id = fields.Many2one('wizard.order.process.transaction')
    ref_no = fields.Char('Transaction Ref', compute="_compute_ref_no")
    new_trans_ref_id = fields.Char('Transaction')

    def _compute_ref_no(self):
        self.ref_no = self.transaction_id.acquirer_reference
        
    def void_transaction(self):
        self.transaction_id.s2s_void_transaction()
        return True

    def proceed_with(self):
        if self.transaction_id.payment_id:
            try:
                if not self.transaction_id:
                    self.transaction_id.payment_id.action_post()
                    return True
                if self.transaction_id.payment_id.transaction_command == "Sale":
                    self.transaction_id._set_transaction_done()
                    self.transaction_id.payment_id.with_context().action_post()
                    return True
            except:
                pass
        return True