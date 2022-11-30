# -*- coding: utf-8 -*-
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    
    tax_line_ids = fields.One2many('account.tax.payment', 'payment_id', string='Payment')
    tax_cpr_number = fields.Char(string='CPR#')
    ext_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        domain="[('company_id', '=', company_id)]",
        check_company=True)
    is_lock_entry = fields.Boolean(string='Lock GL')
    total_wht_tax_amount = fields.Float(string='WHT Amount', compute='_compute_tax_amount')
    wht_percentage = fields.Float(string='Percentage')
    
    
    @api.depends('tax_line_ids')
    def _compute_tax_amount(self):
        for line in self:
            total_amount = 0
            preceding_tax = 0
            count_prece_tax = 0
            for tax_line in line.tax_line_ids:
                count_prece_tax += 1
                if count_prece_tax==1:
                    preceding_tax += tax_line.tax_id.amount
                total_amount += tax_line.amount
            line.total_wht_tax_amount = total_amount 
            line.wht_percentage = preceding_tax
                
          
    
    
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                self.payment_method_line_id.name, self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        write_off_balance = self.currency_id._convert(
            write_off_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id
        total_wht_amount = 0
        for line in self.tax_line_ids:
            total_wht_amount += line.amount
        de_liquidity_balance = liquidity_balance - total_wht_amount
        ce_liquidity_balance = liquidity_balance + total_wht_amount

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else: # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = self._prepare_payment_display_name()

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': de_liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -ce_liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.ext_account_id.id if self.ext_account_id else self.destination_account_id.id,
            },
            
        ]
        for tax_line in self.tax_line_ids:
            line_vals_list.append({
                'name': 'Tax Applied '+str(tax_line.tax_id.name)+' '+str(tax_line.invoice_id.name if tax_line.invoice_id else '')+'  '+str(self.payment_reference or default_line_name),
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': tax_line.amount if liquidity_balance > 0.0 else 0.0,
                'credit': tax_line.amount if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': tax_line.tax_id.invoice_repartition_line_ids.account_id.id,
            },)

        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off line.
            line_vals_list.append({
                'name': write_off_line_vals.get('name') or default_line_name,
                'amount_currency': write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id'),
            })
        return line_vals_list

    
    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.payment <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                if len(counterpart_lines) != 1:
                    pass

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    pass

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))
                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    pass

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))
    
    
    
    
class AccountTaxPayment(models.Model):
    _name='account.tax.payment'
    _description = 'Account Tax Payment'
    
    
    tax_id = fields.Many2one('account.tax', string='Tax', required=True )
    payment_id = fields.Many2one('account.payment', string='Payment')
    partner_id = fields.Many2one('res.partner', string='Partner')
    include_tax_id = fields.Many2one('account.tax', string='Include Tax')
    invoice_id = fields.Many2one('account.move',  string='Invoice', domain="[('state','=','posted'),('payment_state','in',('not_paid','in_payment','partial')),('partner_id','=',partner_id)]")
    inv_amount = fields.Float(string='INV Amount')
    amount = fields.Float(string='Amount')
    
    @api.onchange('payment_id')
    def onchange_payment(self):
        for line in self:
            if line.payment_id:
                line.partner_id = line.payment_id.partner_id.id
   
    
    
    
    
    
    @api.onchange('invoice_id')
    def onchange_invoice(self):
        for line in self:
            if line.invoice_id:
                line.inv_amount = line.invoice_id.amount_total
    
    @api.onchange('tax_id' ,'include_tax_id','inv_amount')
    def onchange_tax(self):
        for line in self:
            include_tax = 0
            if line.include_tax_id:
                include_tax = (abs(line.include_tax_id.amount) / 100 * self.payment_id.amount)  
            if line.invoice_id:
                line.amount = (abs(line.tax_id.amount) / 100 * (line.inv_amount) )    
            else:    
                line.amount = (abs(line.tax_id.amount) / 100 * (self.payment_id.amount + include_tax) )
           

