# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import EbizChargeAPI


class EmailReceipt(models.Model):
    """
    Niaz implementation
    Model used to maintain the record of receipts
    """

    _name = 'email.receipt'

    name = fields.Char(string='Name')
    receipt_subject = fields.Char(string='Subject')
    receipt_from_email = fields.Char(string='From Email')
    receipt_id = fields.Char(string='Receipt ID')
    auto_get_receipts = fields.Char(string="Auto Get Receipts", compute='get_receipts')
    target = fields.Char(string='Target')
    content_type = fields.Char(string='Content Type')

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super(EmailReceipt, self).search_read(domain, fields, offset, limit, order)
        if not self.env['email.receipt'].search([]):
            self.get_receipts()
        return res

    def get_receipts(self):
        """
            Niaz implementation
            Fetch email receipts
            """
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            receipts = ebiz.client.service.GetReceiptsList(**{
                'securityToken': ebiz._generate_security_json(),
                'receiptType': 'Email',
            })

            if receipts:
                for template in receipts:
                    odoo_temp = self.env['email.receipt'].search([('receipt_id', '=', template['ReceiptRefNum'])])
                    if not odoo_temp:
                        self.env['email.receipt'].create({
                            'name': template['Name'],
                            'receipt_subject': template['Subject'],
                            'receipt_from_email': template['FromEmail'],
                            'receipt_id': template['ReceiptRefNum'],
                            'target': template['Target'],
                            'content_type': template['ContentType'],
                        })

            self.auto_get_receipts = False
            # self.env.cr.commit()

        except Exception as e:
            raise ValidationError(e)