# -- coding: utf-8 --


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
        invoice_order = self.env['account.move'].browse((docids[0]))
        for rec in invoice_order:
            product_data = []
            for i in rec.invoice_line_ids:
                try:
                    if i.product_id.sh_is_bundle:
                        size_range, assortment, product_color, product_name = self.product_name_size_range(i)
                        dict_exist = next(
                            (item for item in product_data if item['product_id'] ==
                             i.product_id.id), None)
                        if not dict_exist:
                            new_dict = {
                                'product_id': i.product_id.id,
                                'product_name': product_name.upper(),
                                'color': product_color,
                                'color_id': None,
                                'size_range': size_range,
                                'assortment': assortment,
                                'line_total_qty': i.quantity,
                                'line_qty': i.quantity,
                                'retail_price': i.price_unit,
                                'pair_price': i.product_id.x_studio_pair_price,
                                'price_unit': i.price_unit,
                                'line_subtotal': i.price_subtotal,
                                'uom': i.product_uom_id.name if i.product_uom_id else None,
                                'sizes': [{
                                    '36': 0,
                                    '37': 0,
                                    '38': 0,
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
                            for line in i.product_id.product_tmpl_id.sh_bundle_product_ids:
                                product_attribute = line.sh_product_id.product_template_attribute_value_ids
                                size = product_attribute.filtered(
                                    lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                                )
                                new_dict['sizes'][0][size.name] += i.quantity * line.sh_qty
                            product_data.append(new_dict)
                        else:
                            for line in i.product_id.product_tmpl_id.sh_bundle_product_ids:
                                product_attribute = line.sh_product_id.product_template_attribute_value_ids
                                size = product_attribute.filtered(
                                    lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                                )
                                dict_exist['sizes'][0][size.name] += i.quantity * line.sh_qty
                    else:
                        self.create_variant_line(rec, i, product_data)
                except Exception as e:
                    self.create_line_without_qty(product_data, i, product_data)

        return {
            'doc_model': 'account.move',
            'doc': invoice_order,
            'data': data,
            'product_data': product_data,
        }

    def get_color_name(self, product):
        for rec in product:
            if rec.sh_bundle_product_ids:
                for line in rec.sh_bundle_product_ids:
                    product_attribute = line.sh_product_id.product_template_attribute_value_ids
                    color_id = product_attribute.filtered(
                        lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                    )
                    return color_id.name
            else:
                product_attribute = product.product_template_attribute_value_ids
                color_id = product_attribute.filtered(
                    lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
                )
                return color_id.name

    def get_assortment_size_range(self, product=None):
        size_range = []
        assortment = []
        for rec in product:
            if rec.sh_bundle_product_ids:
                for assort in rec.sh_bundle_product_ids:
                    assortment.append(int(assort.sh_qty))
                for size in rec.sh_bundle_product_ids:
                    product_attribute = size.sh_product_id.product_template_attribute_value_ids
                    size = product_attribute.filtered(
                        lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
                    )
                    size_range.append(size.name)
                assortment = '-'.join([str(assortment[i]) for i in range(len(assortment))])
                size_range = min(size_range) + '-' + max(size_range)
                return '(' + size_range + ')', '(' + assortment + ')'
            else:
                return assortment, size_range

    def create_line_without_qty(self, variant_values=None, i=None, product_data=None):
        dict_exist = next(
            (item for item in product_data if item['product_id'] ==
             i.product_id.id), None)
        if not dict_exist:
            variant_values.append({
                'product_id': i.product_id.id,
                'product_name': i.product_id.name.upper(),
                'color': '-',
                'color_id': '',
                'size_range': None,
                'assortment': '-',
                'retail_price': i.price_unit,
                'price_unit': i.price_unit,
                'line_total_qty': i.quantity,
                'line_qty': i.quantity,
                'line_subtotal': i.price_subtotal,
                'pair_price': i.product_id.x_studio_pair_price,
                'uom': i.product_uom_id.name if i.product_uom_id else None,
                'sizes': [{
                    '36': 0,
                    '37': 0,
                    '38': 0,
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
        else:
            dict_exist['line_total_qty'] += i.product_qty
            dict_exist['line_qty'] += i.product_qty
            dict_exist['line_subtotal'] += i.price_subtotal
        return variant_values

    def create_variant_line(self, invoice=None, inv_line=None, product_data=None):
        if inv_line.product_id.product_tmpl_id:
            product_attribute = inv_line.product_id.product_template_attribute_value_ids
            color_id = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'COLOR'
            )
            size = product_attribute.filtered(
                lambda attribute: attribute.attribute_id.name.upper() == 'SIZE'
            )
            dict_exist = next(
                (item for item in product_data if item['color_id'] ==
                 color_id.id), None)
            if not dict_exist:
                new_dict = {
                    'product_id': inv_line.product_id.id,
                    'product_name': inv_line.product_id.name.upper(),
                    'color': color_id.name,
                    'color_id': color_id.id,
                    'size_range': '(36-46)',
                    'assortment': '-',
                    'line_total_qty': inv_line.quantity,
                    'line_qty': inv_line.quantity,
                    'retail_price': inv_line.price_unit,
                    'price_unit': inv_line.price_unit,
                    'line_subtotal': inv_line.price_subtotal,
                    'pair_price': inv_line.product_id.x_studio_pair_price,
                    'uom': inv_line.product_uom_id.name if inv_line.product_uom_id else None,
                    'sizes': [{
                        '36': 0,
                        '37': 0,
                        '38': 0,
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
                new_dict['sizes'][0][size.name] += inv_line.quantity
                product_data.append(new_dict)
            else:
                dict_exist['sizes'][0][size.name] += inv_line.quantity

        else:
            self.create_line_without_qty(product_data, inv_line, product_data)

    def product_name_size_range(self, invoice_line=None):
        # get product_name , color, size_range, Assortment
        color_name = self.get_color_name(invoice_line.product_id)
        size_range, assortment = self.get_assortment_size_range(invoice_line.product_id)
        product_combine_name = invoice_line.product_id.name
        split_res = product_combine_name.split('-')
        product_name = ''
        product_color = ''
        for col in split_res:
            if color_name.upper() == col.upper():
                product_color = col
                product_name = product_name[:-1]
                break
            else:
                product_name += col + '-'
        return size_range, assortment, product_color, product_name.upper()