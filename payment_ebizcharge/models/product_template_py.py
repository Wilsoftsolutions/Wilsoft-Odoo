# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from .ebiz_charge import EbizChargeAPI
from datetime import datetime, timedelta

time_spam = False


class SyncProductss(models.Model):

    _inherit = 'product.template'

    ebiz_product_internal_id = fields.Char(string='Ebiz Product Internal ID', copy=False)
    ebiz_product_id = fields.Char(string='Ebiz Product ID', copy=False)
    sync_status = fields.Char(string='Sync Status', readonly='True')
    last_sync_date = fields.Datetime(string="Upload Date & Time", copy=False)
    sync_responce = fields.Char(string="Sync Status", copy=False)
    upload_status = fields.Char(string="EBizCharge Upload Status", compute="_compute_sync_status")

    def _compute_sync_status(self):
        for order in self:
            order.upload_status = "Synchronized" if order.ebiz_product_internal_id else "Pending"

    def _compute_button_auto_check(self):
        config = self.env['res.config.settings'].sudo().default_get([])
        self.auto_sync_button = config.get('ebiz_auto_sync_products', False)

    auto_sync_button = fields.Boolean(compute="_compute_button_auto_check", default=False)

    def import_ebiz_products(self):

        """
        Niaz Implementation:
        Getting All Ebiz Products to Odoo Products.

        Added button at random position(Product Form), further on the position will be set according to PM instructions
        """

        try:
            config = self.env['res.config.settings'].default_get([])
            security_key = config.get('ebiz_security_key')
            user_id = config.get('ebiz_user_id')
            password = config.get('ebiz_password')

            if not security_key or not user_id or not password:
                raise UserError(f'Dear "{self.env.user.name}," You Have Not Entered The Ebiz Credentials!')

            # ebiz = ebiz = EbizChargeAPI(security_key, user_id, password)
            if hasattr(self, 'website_id'):
                ebiz = self.get_ebiz_charge_obj(self.website_id.id)
            else:
                ebiz = self.get_ebiz_charge_obj()
            # print('debuger')

            get_all_products = ebiz.client.service.SearchItems(**{
                'securityToken': {'SecurityId': security_key, 'UserId': user_id, 'Password': password},
                'start': 0,
                'limit': 1000000,
            })

            if get_all_products != None:
                for product in get_all_products:
                    odoo_product = self.env['product.template'].search([('ebiz_product_internal_id', '=', product['ItemInternalId']),
                                                                    ('ebiz_product_id', '=', product['ItemId'])])
                    if not odoo_product:

                        product_data = {
                            'name': product['Name'],
                            'description': product['Description'],
                            'list_price': product['UnitPrice'],
                            'type': 'service' if product['ItemType'] == 'Service' else 'consu' if product['ItemType'] =='inventory' else None,
                            'barcode': product['SKU'] if product['SKU'] != 'False' else '',
                            'ebiz_product_id': product['ItemId'] if product['ItemId'] else '',
                            'ebiz_product_internal_id': product['ItemInternalId'],
                        }
                        # print('debugger')

                        self.env['product.template'].create(product_data)
                        self.env.cr.commit()

                context = dict(self._context)
                context['message'] = 'Sucessful!'
                return self.message_wizard(context)

            else:
                raise UserError('No New Product To Import!')

        except UserError as e:
            raise UserError('No New Product To Import!')

        except Exception as e:
            raise UserError('Something Went Wrong!')

    def add_update_to_ebiz_ind(self):
        return self.with_context({'message_bypass': True}).add_update_to_ebiz()

    def add_update_to_ebiz(self, list_of_products=None):
        """
            Niaz Implementation:
            Update Products
        """

        try:
            
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            resp_lines = []
            resp_line = {}
            success = 0
            failed = 0

            if list_of_products:
                self = products_records = self.env['product.template'].browse(list_of_products).exists()

            total = len(self)
            for product in self:
                if list_of_products:
                    reference_to_upload_product = self.env['list.of.products'].search([('product_id', '=', product.id)])
                    reference_to_upload_product.last_sync_date = datetime.now()

                resp_line = {
                    'record_name': product.name
                }

                tax_amount = 0
                total_tax = 0
                if product['taxes_id']:
                    for tax_id in product['taxes_id']:
                        if tax_id['amount_type'] == 'percent':
                            tax_amount = (product['list_price'] * tax_id['amount']) / 100
                        elif tax_id['amount_type'] == 'fixed':
                            tax_amount = tax_id['amount']
                        elif tax_id['amount_type'] == 'group':
                            for child in tax_id.children_tax_ids:
                                if child['amount_type'] == 'percent':
                                    tax_amount += (product['list_price'] * child['amount']) / 100
                                elif child['amount_type'] == 'fixed':
                                    tax_amount += child['amount']

                        total_tax += tax_amount

                product_details = {
                    'Name': product['name'],
                    'Description': product['name'],
                    'UnitPrice': product['list_price'],
                    'UnitCost': product['standard_price'] if product['standard_price'] else product['list_price'],
                    'Active': True,
                    'ItemType': 'Service' if product['type'] == 'service' else 'inventory',
                    'SKU': product['barcode'] if product['barcode'] else '',
                    'Taxable': True if product['taxes_id'] else False,
                    'TaxRate': total_tax,
                    'ItemNotes': product['description'] if product['description'] else '',
                    # 'ItemUniqueId': '12345',
                    'ItemId': product.id,
                    'SoftwareId': 'Odoo CRM',
                    'QtyOnHand': int(product.qty_available) if 'qty_available' in product else 0,
                }

                if product.ebiz_product_internal_id and product.ebiz_product_id:
                    update = ebiz.client.service.UpdateItem(**{
                        'securityToken': ebiz._generate_security_json(),
                        'itemInternalId': product.ebiz_product_internal_id,
                        'itemId': product.ebiz_product_id,
                        'itemDetails': product_details,
                    })
                    resp_line['record_message'] = update['Error'] or update['Status']
                    product.sync_status = 'Synchronized'
                    product.sync_responce = update.Status
                    if product.sync_responce == 'Success':
                        product.last_sync_date = datetime.now()
                        success += 1

                    else:
                        failed += 1

                    resp_lines.append([0, 0, resp_line])
                    if product:
                        self.env['logs.of.products'].create({
                            'product_name': product.id,
                            'sync_status': update.Status,
                            'last_sync_date': datetime.now(),
                            'sync_log_id': 1,
                            'user_id': self.env.user.id,
                            'internal_reference': product.default_code,
                            'name': product.name,
                            'sales_price': product.list_price,
                            'cost': product.standard_price,
                            'quantity': product.qty_available,
                            'type': product.type,
                        })
                        product.sync_status = update.Status

                else:
                    create = ebiz.client.service.AddItem(**{
                        'securityToken': ebiz._generate_security_json(),
                        'itemDetails': product_details,
                    })
                    resp_line['record_message'] = create['Error'] or create['Status']
                    if create.Status == 'Success':
                        product.ebiz_product_internal_id = create['ItemInternalId']
                        product.ebiz_product_id = product.id
                        product.sync_status = 'Synchronized'
                        product.sync_responce = create.Status
                        product.last_sync_date = datetime.now()
                        success += 1
                        resp_lines.append([0, 0, resp_line])

                        if list_of_products:
                            self.env['logs.of.products'].create({
                                'product_name': product.id,
                                'sync_status': create.Status,
                                'last_sync_date': datetime.now(),
                                'sync_log_id': 1,
                                'user_id': self.env.user.id,
                                'internal_reference': product.default_code,
                                'name': product.name,
                                'sales_price': product.list_price,
                                'cost': product.standard_price,
                                'quantity': product.qty_available,
                                'type': product.type,
                            })
                            reference_to_upload_product.sync_status = create.Status

                    elif create.Error == 'Record already exists':
                        update = ebiz.client.service.UpdateItem(**{
                            'securityToken': ebiz._generate_security_json(),
                            # 'itemInternalId': product.ebiz_product_internal_id,
                            'itemId': product.id,
                            'itemDetails': product_details,
                        })
                        resp_line['record_message'] = update['Error'] or update['Status']
                        product.sync_status = 'Synchronized'
                        product.ebiz_product_internal_id = update['ItemInternalId']
                        product.sync_responce = update.Status
                        if product.sync_responce == 'Success':
                            product.last_sync_date = datetime.now()
                            success += 1

                        else:
                            failed += 1
                        resp_lines.append([0, 0, resp_line])
                        # raise UserError('Record already exists.')

                        if list_of_products:
                            self.env['logs.of.products'].create({
                                'product_name': product.id,
                                'sync_status': create.Status,
                                'last_sync_date': datetime.now(),
                                'sync_log_id': 1,
                                'user_id': self.env.user.id,
                                'internal_reference': product.default_code,
                                'name': product.name,
                                'sales_price': product.list_price,
                                'cost': product.standard_price,
                                'quantity': product.qty_available,
                                'type': product.type,
                            })
                            reference_to_upload_product.sync_status = create.Status

                    else:
                        failed += 1
                        resp_lines.append([0, 0, resp_line])
                        # raise UserError('Something Went Wrong! Try Again!')

                        if list_of_products:
                            self.env['logs.of.products'].create({
                                'product_name': product.id,
                                'sync_status': create.Status,
                                'last_sync_date': datetime.now(),
                                'sync_log_id': 1,
                                'user_id': self.env.user.id,
                                'internal_reference': product.default_code,
                                'name': product.name,
                                'sales_price': product.list_price,
                                'cost': product.standard_price,
                                'quantity': product.qty_available,
                                'type': product.type,
                            })
                            reference_to_upload_product.sync_status = create.Status

            if self.env.context.get('message_bypass'):
                context = dict(self._context)
                context['message'] = 'Product uploaded successfully!'
                return self.message_wizard(context)
            else:
                wizard = self.env['wizard.multi.sync.message'].create(
                    {'name': 'products', 'lines_ids': resp_lines,
                    'success_count': success, 'failed_count': failed, 'total': total})
                action = self.env.ref('payment_ebizcharge.wizard_multi_sync_message_action').read()[0]
                action['context'] = self._context
                action['res_id'] = wizard.id
                return action

        except Exception as e:
            resp_line['record_message'] = str(e)
            raise ValidationError("Please try again later.")

    def message_wizard(self, context):
        """
            Niaz Implementation:
            Generic Function for sucessfull message indication for the user to enhance user experince
            param: Message string will be passed to context
            returrn: wizard
        """

        return {
            'name': ('Success'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    @api.model
    def create(self, values):
        config = self.env['res.config.settings'].default_get([])
        product = super(SyncProductss, self).create(values)
        if config.get('ebiz_auto_sync_products'):
            product.add_update_to_ebiz()
        return product

    def write(self, values):
        # active_prodcut = self.env['product.template'].browse(self.env.context.get('active_id'))
        product = super(SyncProductss, self).write(values)
        if self.ebiz_product_internal_id and 'ebiz_product_internal_id' not in values and 'ebiz_product_id' not in\
                values and 'last_sync_date' not in values and 'sync_responce' not in values and  'sync_status' not in values:
            self.add_update_to_ebiz()
            return product
        else:
            return product


class SyncQuantity(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def create(self, values):
        quantity = super(SyncQuantity, self).create(values)
        product = self.product_id
        if self.product_id.ebiz_product_internal_id and self.product_id.ebiz_product_id and 'inventory_quantity' in values:

            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            update = ebiz.client.service.UpdateItem(**{
                'securityToken': ebiz._generate_security_json(),
                'itemInternalId': product.ebiz_product_internal_id,
                'itemId': product.ebiz_product_id,
                'itemDetails': {
                    'QtyOnHand': self.quantity if 'qty_available' in product else 0,
                },
            })
            self.env['logs.of.products'].create({
                'product_name': product.id,
                'sync_status': update.Status,
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,
                'internal_reference': product.default_code,
                'name': product.name,
                'sales_price': product.list_price,
                'cost': product.standard_price,
                'quantity': product.qty_available,
                'type': product.type,
            })
            return quantity
        else:
            return quantity

    def write(self, values):
        quantity = super(SyncQuantity, self).write(values)
        product = self.product_id
        if self.product_id.ebiz_product_internal_id and self.product_id.ebiz_product_id and 'inventory_quantity' in values:
            
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()
            
            update = ebiz.client.service.UpdateItem(**{
                'securityToken': ebiz._generate_security_json(),
                'itemInternalId': product.ebiz_product_internal_id,
                'itemId': product.ebiz_product_id,
                'itemDetails': {
                    'QtyOnHand': self.quantity if 'qty_available' in product else 0,
                },
            })
            self.env['logs.of.products'].create({
                'product_name': product.id,
                'sync_status': update.Status,
                'last_sync_date': datetime.now(),
                'sync_log_id': 1,
                'user_id': self.env.user.id,
                'internal_reference': product.default_code,
                'name': product.name,
                'sales_price': product.list_price,
                'cost': product.standard_price,
                'quantity': product.qty_available,
                'type': product.type,
            })
            return quantity
        else:
            return quantity

