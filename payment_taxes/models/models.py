# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountTaxInherit(models.Model):
	_inherit = 'account.tax'

	is_withholding = fields.Boolean(
		string='Is withholding',
		required=False)


class AccountPaymentInherit(models.Model):
	_inherit = 'account.payment'

	tax_type = fields.Many2one(
		comodel_name='account.tax',
		string='Tax Type',
		required=False
	)

	is_withholding_amount = fields.Float(string='Is withholding Amount', store=True)
	tax_type_check = fields.Char('Tax categ', compute="get_tax_type_check")

	@api.depends('journal_id')
	def get_tax_type_check(self):
		if self.payment_type == 'inbound':
			self.tax_type_check = 'sale'
		if self.payment_type == 'outbound':
			self.tax_type_check = 'purchase'

	@api.onchange('tax_type', 'amount')
	def onchange_tax_type(self):
		for rec in self:
			if rec.tax_type.is_withholding:
				rec.is_withholding_amount = (rec.tax_type.amount / 100 * self.amount)
			else:
				rec.is_withholding_amount = 0.0

	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
		            * amount:       The amount to be added to the counterpart amount.
		            * name:         The label to set on the line.
		            * account_id:   The account on which create the write-off.
		        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		        '''
		self.ensure_one()
		for rec in self:

			if rec.tax_type.is_withholding:
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
				de = liquidity_balance - self.is_withholding_amount
				ce = liquidity_balance + self.is_withholding_amount
				counters = self.is_withholding_amount
				currency_id = self.currency_id.id

				if self.is_internal_transfer:
					if self.payment_type == 'inbound':
						liquidity_line_name = _('Transfer to %s', self.journal_id.name)
					else:  # payment.payment_type == 'outbound':
						liquidity_line_name = _('Transfer from %s', self.journal_id.name)
				else:
					liquidity_line_name = self.payment_reference

				# Compute a default label to set on the journal items.

				payment_display_name = {
					'outbound-customer': _("Customer Reimbursement"),
					'inbound-customer': _("Customer Payment"),
					'outbound-supplier': _("Vendor Payment"),
					'inbound-supplier': _("Vendor Reimbursement"),
				}

				default_line_name = self.env['account.move.line']._get_default_line_name(
					_("Internal Transfer") if self.is_internal_transfer else payment_display_name[
						'%s-%s' % (self.payment_type, self.partner_type)],
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
						'debit': de if liquidity_balance > 0.0 else 0.0,
						'credit': -ce if liquidity_balance < 0.0 else 0.0,
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
						'account_id': self.destination_account_id.id,
					},
					{
						'name': self.payment_reference or default_line_name,
						'date_maturity': self.date,
						'amount_currency': counterpart_amount_currency,
						'currency_id': currency_id,
						'debit': counters if liquidity_balance > 0.0 else 0.0,
						'credit': counters if liquidity_balance < 0.0 else 0.0,
						'partner_id': self.partner_id.id,
						'account_id': rec.tax_type.invoice_repartition_line_ids.account_id.id,
					},

				]
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
			else:
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

				if self.is_internal_transfer:
					if self.payment_type == 'inbound':
						liquidity_line_name = _('Transfer to %s', self.journal_id.name)
					else:  # payment.payment_type == 'outbound':
						liquidity_line_name = _('Transfer from %s', self.journal_id.name)
				else:
					liquidity_line_name = self.payment_reference

				# Compute a default label to set on the journal items.

				payment_display_name = {
					'outbound-customer': _("Customer Reimbursement"),
					'inbound-customer': _("Customer Payment"),
					'outbound-supplier': _("Vendor Payment"),
					'inbound-supplier': _("Vendor Reimbursement"),
				}

				default_line_name = self.env['account.move.line']._get_default_line_name(
					_("Internal Transfer") if self.is_internal_transfer else payment_display_name[
						'%s-%s' % (self.payment_type, self.partner_type)],
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
						'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
						'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
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
						'account_id': self.destination_account_id.id,
					},
					# {
					# 	'name': self.payment_reference or default_line_name,
					# 	'date_maturity': self.date,
					# 	'amount_currency': counterpart_amount_currency,
					# 	'currency_id': currency_id,
					# 	'debit': 0.0,
					# 	'credit': 0.0,
					# 	'partner_id': self.partner_id.id,
					# 	'account_id': self.journal_id.id,
					# },

				]
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


class AccountPaymentRegisterInherit(models.TransientModel):
	_inherit = 'account.payment.register'

	tax_types = fields.Many2one(
		comodel_name='account.tax',
		string='Tax Type',
		required=False, )

	is_withholding_amounts = fields.Float(string='Is withholding Amount', readonly=True, store=True)
	tax_type_checks = fields.Char('Tax categ', compute="get_tax_type_checks")

	@api.depends('journal_id')
	def get_tax_type_checks(self):
		if self.payment_type == 'inbound':
			self.tax_type_checks = 'sale'
		if self.payment_type == 'outbound':
			self.tax_type_checks = 'purchase'


	@api.onchange('tax_types', 'amount')
	def onchange_tax_types(self):
		for rec in self:
			if rec.tax_types.is_withholding:
				rec.is_withholding_amounts = (rec.tax_types.amount / 100 * self.amount)
			else:
				rec.is_withholding_amounts = 0.0

	def _create_payment_vals_from_wizard(self):
		for rec in self:
			if rec.is_withholding_amounts:
				payment_vals = {
					'date': self.payment_date,
					'amount': self.amount,
					'is_withholding_amount': self.is_withholding_amounts,
					'tax_type': self.tax_types.id,
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

				if not self.currency_id.is_zero(
						self.payment_difference) and self.payment_difference_handling == 'reconcile':
					payment_vals['write_off_line_vals'] = {
						'name': self.writeoff_label,
						'amount': self.payment_difference,
						'account_id': self.writeoff_account_id.id,
					}
				return payment_vals
			else:
				payment_vals = {
					'date': self.payment_date,
					'amount': self.amount,
					'is_withholding_amount': self.is_withholding_amounts,
					'tax_type': self.tax_types.id,
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

				if not self.currency_id.is_zero(
						self.payment_difference) and self.payment_difference_handling == 'reconcile':
					payment_vals['write_off_line_vals'] = {
						'name': self.writeoff_label,
						'amount': self.payment_difference,
						'account_id': self.writeoff_account_id.id,
					}
				return payment_vals

	def create_payment_vals_from_wizards(self):
		for rec in self:
			if rec.is_withholding_amounts:
				payment_vals = {
					'date': self.payment_date,
					'amount': self.amount,
					'is_withholding_amount': self.is_withholding_amounts,
					'tax_type': self.tax_types.id,
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
				if not self.currency_id.is_zero(
						self.payment_difference) and self.payment_difference_handling == 'reconcile':
					payment_vals['write_off_line_vals'] = {
						'name': self.writeoff_label,
						'amount': self.payment_difference,
						'account_id': self.writeoff_account_id.id,
					}
				return payment_vals

	def _create_payments(self):
		self.ensure_one()
		batches = self._get_batches()
		edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)

		to_reconcile = []
		if edit_mode:
			payment_vals = self._create_payment_vals_from_wizard()
			aa = self.create_payment_vals_from_wizards()
			if aa:
				payment_vals_list = [payment_vals, aa]
			else:
				payment_vals_list = [payment_vals]
			to_reconcile.append(batches[0]['lines'])
		else:
			# Don't group payments: Create one batch per move.
			if not self.group_payment:
				new_batches = []
				for batch_result in batches:
					for line in batch_result['lines']:
						new_batches.append({
							**batch_result,
							'lines': line,
						})
				batches = new_batches

			payment_vals_list = []
			for batch_result in batches:
				payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
				to_reconcile.append(batch_result['lines'])

		payments = self.env['account.payment'].create(payment_vals_list)

		# If payments are made using a currency different than the source one, ensure the balance match exactly in
		# order to fully paid the source journal items.
		# For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
		# If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
		if edit_mode:
			for payment, lines in zip(payments, to_reconcile):
				# Batches are made using the same currency so making 'lines.currency_id' is ok.
				if payment.currency_id != lines.currency_id:
					liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
					source_balance = abs(sum(lines.mapped('amount_residual')))
					payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
					source_balance_converted = abs(source_balance) * payment_rate

					# Translate the balance into the payment currency is order to be able to compare them.
					# In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
					# attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
					# match.
					payment_balance = abs(sum(counterpart_lines.mapped('balance')))
					payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
					if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
						continue

					delta_balance = source_balance - payment_balance

					# Balance are already the same.
					if self.company_currency_id.is_zero(delta_balance):
						continue

					# Fix the balance but make sure to peek the liquidity and counterpart lines first.
					debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
					credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

					payment.move_id.write({'line_ids': [
						(1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
						(1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
					]})

		payments.action_post()

		domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
		for payment, lines in zip(payments, to_reconcile):

			# When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
			# and then, we can't perform the reconciliation.
			if payment.state != 'posted':
				continue

			payment_lines = payment.line_ids.filtered_domain(domain)
			for account in payment_lines.account_id:
				(payment_lines + lines) \
					.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
					.reconcile()

		return payments
