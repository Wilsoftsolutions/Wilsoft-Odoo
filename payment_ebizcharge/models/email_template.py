# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ebiz_charge import EbizChargeAPI


class EmailTemplates(models.Model):
    """
        Niaz implementation
        Model used to maintain the record of Email Templates
        """

    _name = 'email.templates'

    name = fields.Char(string='Name')
    template_id = fields.Char(string='Email Templates ID')
    template_subject = fields.Char(string='Subject')
    template_description = fields.Char(string='Description')
    template_type_id = fields.Char(string='Type ID')
    auto_get_templates = fields.Char(string="Auto Get Receipts", compute='get_templates')

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super(EmailTemplates, self).search_read(domain, fields, offset, limit, order)
        if not self.env['email.templates'].search([]):
            self.get_templates()
        return res

    def get_templates(self):
        """
            Niaz implementation
            Used to fetch Email Receipts
            """
        try:
            ebiz = self.env['ebiz.charge.api'].get_ebiz_charge_obj()

            templates = ebiz.client.service.GetEmailTemplates(**{
                'securityToken': ebiz._generate_security_json()
            })

            if templates:
                for template in templates:
                    odoo_temp = self.env['email.templates'].search([('template_id', '=', template['TemplateInternalId'])])
                    if not odoo_temp:
                        self.env['email.templates'].create({
                            'name': template['TemplateName'],
                            'template_id': template['TemplateInternalId'],
                            'template_subject': template['TemplateSubject'],
                            'template_description': template['TemplateDescription'],
                            'template_type_id': template['TemplateTypeId'],
                        })
                    else:
                        odoo_temp.write({
                            'template_subject': template['TemplateSubject'],
                        })

            
            self.auto_get_templates = False
            # self.env.cr.commit()

        except Exception as e:
            raise ValidationError(e)