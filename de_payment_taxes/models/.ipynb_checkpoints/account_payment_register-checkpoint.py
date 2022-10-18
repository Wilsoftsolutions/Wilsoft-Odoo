# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ 


class AccountPayment(models.TransientModel):
    _inherit = 'account.payment.register'
    
    
    tax_line_ids = fields.One2many('account.tax.payment.line', 'payment_register_id', string='Payment')
    
    
    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self):
        tax_list = []
        for tax_line in self.tax_line_ids:
            tax_list.append((0,0,{
              'tax_id': tax_line.tax_id.id,
              'include_tax_id': tax_line.include_tax_id.id,
              'invoice_id':tax_line.invoice_id.id,
              'inv_amount': tax_line.inv_amount,
              'amount': tax_line.amount,
            }))    
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'tax_line_ids': tax_list,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        return payment_vals
    
    
    
    
class AccountTaxPayment(models.TransientModel):
    _name='account.tax.payment.line'
    _description = 'Account Tax Payment Line'
    
    
    tax_id = fields.Many2one('account.tax', string='Tax', required=True )
    payment_register_id = fields.Many2one('account.payment.register', string='Payment Register')
    include_tax_id = fields.Many2one('account.tax', string='Include Tax')
    invoice_id = fields.Many2one('account.move',  string='Invoice')
    inv_amount = fields.Float(string='INV Amount')
    amount = fields.Float(string='Tax Amount')
    
    @api.onchange('invoice_id')
    def onchange_invoice(self):
        for line in self:
            if line.invoice_id:
                line.inv_amount = line.invoice_id.amount_total
    
    @api.onchange('tax_id' ,'include_tax_id')
    def onchange_tax(self):
        for line in self:
            include_tax = 0            
            if line.include_tax_id:
                include_tax = (abs(line.include_tax_id.amount) / 100 * line.payment_register_id.amount)
            if line.invoice_id:
                line.amount = (abs(line.tax_id.amount) / 100 * (line.inv_amount) )
            else:    
                line.amount = (abs(line.tax_id.amount) / 100 * (line.payment_register_id.amount + include_tax) )    