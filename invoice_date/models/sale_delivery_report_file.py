# -*- coding: utf-8 -*-


from odoo import models, fields, api


class AccountMoveInherite(models.Model):
    _inherit = 'account.move'

    # @api.multi
    num_words = fields.Char(string="Amount In Words:", compute='_compute_amount_in_words')

    def _compute_amount_in_words(self):
        for rec in self:
            rec.num_words = str(rec.currency_id.amount_to_text(rec.amount_total)) + ' only'




class InvoiceInheritReport(models.AbstractModel):
    _name = 'report.invoice_date.invoice_report_id'
    _description = 'Product Quantity Color and size wise'

    def _get_report_values(self, docids, data=None):
        invoice = self.env['account.move'].browse((docids[0]))
        for rec in invoice:
            variant_values = []
            customer = []
            for i in rec.invoice_line_ids:
                customer.append({
                    'c_name': i.partner_id.name,
                    'address': i.partner_id.street,
                    'phone': i.partner_id.phone,
                    'user':self.env.user.name,
                    'date': rec.invoice_date,
                })
                try:
                    if i.product_id.product_tmpl_id:
                        product_attribute = i.product_id.product_template_attribute_value_ids
                        color_id = product_attribute.filtered(
                            lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                        )
                        size = product_attribute.filtered(
                            lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                        )
                        dict_exist = next(
                            (item for item in variant_values if item['color_id'] ==
                             color_id.id), None)
                        if not dict_exist:
                            new_dict = {
                                'product_name': i.product_id.name,
                                'color_name': color_id.name,
                                'color_id': color_id.id,
                                'uom': i.product_uom_id.name if i.product_uom_id else None,
                                'retail_price': i.product_id.list_price,
                                'line_total_qty': 0,
                                'taxes':rec.amount_tax_signed,
                                'net_amount': rec.amount_total,
                                'sizes': [{
                                    '39': 0,
                                    '40': 0,
                                    '41': 0,
                                    '42': 0,
                                    '43': 0,
                                    '44': 0,
                                    '45': 0,
                                    '46': 0,
                                }]
                            }
                            new_dict['sizes'][0][size.name] += i.quantity
                            variant_values.append(new_dict)
                        else:
                            dict_exist['sizes'][0][size.name] += i.quantity

                    else:
                        self.create_line_without_qty(variant_values, i)

                except Exception:
                    self.create_line_without_qty(variant_values, i)

        return {
            'doc_model': 'account.move',
            'doc': invoice,
            'data': data,
            'c_name': rec.partner_id.name,
            # 'stn_cnic': rec.partner_id.x_studio_cnic,
            # 'stn': rec.partner_id.x_studio_stn,
            'user': self.env.user.name,
            'date': rec.invoice_date,
            'name': rec.name,
            'invoice_origin': rec.invoice_origin,
            'address': rec.partner_id.street,
            'phone': rec.partner_id.phone,
            'variant_values': variant_values,
        }

    def create_line_without_qty(self, variant_values=None, i=None):
        variant_values.append({
            'product_name': i.product_id.name,
            'color_name': '-',
            'color_id': '',
            'uom': i.product_uom_id.name if i.product_uom_id else None,
            'retail_price': i.product_id.list_price,
            'line_total_qty': i.quantity,
            'taxes':i.move_id.amount_tax_signed,
            'net_amount': i.move_id.amount_total,
            'sizes': [{
                '39': 0,
                '40': 0,
                '41': 0,
                '42': 0,
                '43': 0,
                '44': 0,
                '45': 0,
                '46': 0,
            }]
        })
        return variant_values
