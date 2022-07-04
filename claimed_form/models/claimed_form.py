
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PlannedFormModel(models.Model):
    _name = 'claimed.form'
    _rec_name = 'customer_id'

    date = fields.Date("Date")
    serial_number = fields.Char("Sr #",  default='Sr', readonly=True)
    customer_id = fields.Many2one("res.partner", "Customer Name #")
    city = fields.Char(related='customer_id.city', string='City')
    claimed_remark = fields.Char("Claim Remark")
    qc_remark = fields.Char("QC Remark")
    prepared_by = fields.Many2one("res.users", string="Prepared By", default=lambda self: self.env.user )
    qc_by = fields.Char("QC By")
    total_amount = fields.Float("Total" , store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_approval', 'Waiting For Approval'),
        ('waiting_qc_approval', 'Waiting QC Approval'),
        ('waiting_ware_house_approval', 'Waiting W/H Approval'),
        ('approved', 'Approved'),
        # ('reject', 'Rejected'),
        ('cancelled', 'Cancelled')

    ], default='draft')
    claimed_line_ids = fields.One2many("claimed.form.line", 'claimed_id')

    # state changing button are there

    def sent_for_approval(self):
        self.state = 'waiting_for_approval'
        self.claimed_line_ids.check = True

    def qc_approve(self):
        self.state = 'waiting_qc_approval'

    def manager_reject(self):
        self.state = 'cancelled'

    def wh_approval(self):
        self.state = 'waiting_ware_house_approval'

    def approved(self):
        for rec in self:
            current_user = rec.env.uid
            # if picking_id.picking_type_id.code == 'incoming':
            customer_journal_id = rec.env['ir.config_parameter'].sudo().get_param(
                'stock_move_invoice.customer_journal_id')
            journal_id = rec.env['account.journal'].search([('name', '=', 'Customer Invoice')], limit=1)
            if not customer_journal_id:
                invoice_line_list = []
                for i in rec.claimed_line_ids:
                    vals = (0, 0, {
                        # 'name': i.description_picking,
                        'product_id': i.p_id.id,
                        'price_unit': i.unit_price,
                        # 'account_id': i.product_id.property_account_income_id.id if i.product_id.property_account_income_id
                        # else move_ids_without_package.product_id.categ_id.property_account_income_categ_id.id,
                        # 'tax_ids': [(6, 0, [picking_id.company_id.account_sale_tax_id.id])],
                        'quantity': i.qty,
                    })
                    invoice_line_list.append(vals)
                # raise UserError(_("Please configure the journal from settings"))
                credit_note_create = rec.env['account.move'].create({
                    'move_type': 'out_refund',
                    # 'invoice_origin': rec.serial_number,
                    'invoice_user_id': current_user,
                    'narration': rec.serial_number,
                    'partner_id': rec.customer_id.id,
                    'currency_id': rec.env.user.company_id.currency_id.id,
                    'journal_id': int(journal_id),
                    'payment_reference': rec.serial_number,
                    'invoice_line_ids': invoice_line_list
                })
                self.state = 'approved'
                return credit_note_create

    @api.onchange('claimed_line_ids')
    def _onchange_line_id(self):
        for rec in self:
            total = 0
            for line in rec.claimed_line_ids:
                line.unit_price = line.p_id.lst_price
                line.sub_total = line.unit_price * line.qty

                total += line.unit_price * line.qty
                self.total_amount = total

    @api.model
    def create(self, vals_list):
        vals_list['serial_number']= self.env['ir.sequence'].next_by_code('claim_sequence')
        res = super(PlannedFormModel, self).create(vals_list)
        return res


class ClaimedLineModel(models.Model):
    _name = 'claimed.form.line'

    claimed_id = fields.Many2one("claimed.form")
    qty = fields.Integer("Qty")
    p_id = fields.Many2one("product.product", "Article")
    sub_total = fields.Float("Sub Total")
    unit_price = fields.Float("Price Unit")
    check = fields.Boolean(default=False)