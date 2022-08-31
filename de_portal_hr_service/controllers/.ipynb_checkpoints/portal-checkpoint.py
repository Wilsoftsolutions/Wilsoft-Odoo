# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from markupsafe import Markup

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from odoo.http import request
from odoo.tools.translate import _
from odoo.tools import groupby as groupbyelem
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from odoo.osv.expression import OR, AND
import base64
from odoo.tools import safe_eval



import json

class CustomerPortal(portal.CustomerPortal):
    
    def _prepare_service_record_page(self,service_id, model_id, record_id, edit_mode):
        m2o_id = False
        extra_template = ''
        primary_template = ''
        rec_id = 0
        #record_id = 0
        service_id = request.env['hr.service'].sudo().search([('id','=',service_id)],limit=1)
        hr_service_items = False
        record_sudo = False
        record_val = ''
        
        field_val = ''
        field_domain = []
        
        line_item = request.env['hr.service.record.line'].sudo().search([('hr_service_id','=',service_id.id),('line_model_id','=',int(model_id))],limit=1)
        
        if service_id.header_model_id.id == int(model_id):
            hr_service_items = service_id.hr_service_items
            if edit_mode == '1' or edit_mode == 1:
                record_sudo = request.env[service_id.header_model_id.model].sudo().search([('id','=',record_id)],limit=1)
            
            primary_template += '<div class="col-lg-12 text-left mb16" style="border-bottom:1px solid #cccccc;"><h5>' + service_id.header_model_id.name + '</h5></div>'
            extra_template += "<br/>"
            
        elif line_item:
            hr_service_items = line_item.hr_service_record_line_items
            if edit_mode == '1' or edit_mode == 1:
                record_sudo = request.env[line_item.line_model_id.model].sudo().search([('id','=',record_id)],limit=1)
            
            primary_template += '<div class="col-lg-12 text-left mb16" style="border-bottom:1px solid #cccccc;"><h5>' + service_id.header_model_id.name + ' / ' + str(line_item.line_model_id.name) + '</h5></div>'
            extra_template += "<br/>"
                
        
        # ------------------------------------------
        # ------------- Left Section ----------------
        # ------------------------------------------
        for service in service_id:
            for field in hr_service_items.filtered(lambda line: line.display_option == 'left'):
                # find the record value
                field_domain = []
                if record_sudo:
                    if field.sudo().field_id.ttype == 'many2one':
                        record_val = record_sudo[eval("'" + field.field_name + "'")].id
                    else:
                        record_val = str(record_sudo[eval("'" + field.field_name + "'")])
                
                if field.is_required:
                    primary_template += "<div class='form-group col-12 s_website_form_required' data-type='char' data-name='" + field.field_name + "'>"
                else:
                    primary_template += "<div class='form-group col-12' data-type='char' data-name='" + field.field_name + "'>"
                    
                primary_template += "<label class='s_website_form_label' style='width: 200px' for='" + field.field_name + "'>"
                primary_template += "<span class='s_website_form_label_content'>" + field.field_label + "</span>"
                primary_template += "</label>"
                
                # Many2one Field
                if field.field_type == 'many2one':
                    if field.field_model == 'ir.attachment':
                        primary_template += "<input type='file' class='form-control-file s_website_form_input' id='" + field.field_name + "' name='" + field.field_name + "' multiple='1' />"
                    else:
                        field_domain=[]   
                        
                        if field.auto_populate=='employee':
                            field_domain=[('user_id','=',http.request.env.context.get('uid'))]
                        if field.auto_populate=='product':
                            employee_ext = request.env['hr.employee'].search([('user_id','=',http.request.env.context.get('uid'))], limit=1)                    
                            ext_id = employee_ext.employee_type_id.id
                            field_domain=[('employee_type_id' ,'=', ext_id),('can_be_expensed','=',True)]    
                            
                        m2o_id = request.env[field.field_model].sudo().search(field_domain)
                        primary_template += "<select id='" + field.field_name + "' name='" + field.field_name + "'class='form-control' >"
                        for m in m2o_id:
                            primary_template += "<option value='" + str(m.id) + "' " + (" selected" if record_val == m.id else " ") + ">"
                            primary_template += m.name
                            primary_template += "</option>"
                        primary_template += "</select>"
                    
                # Selection field
                elif field.field_type == 'selection':
                    sel_ids = request.env['ir.model.fields.selection'].sudo().search([('field_id','=',field.field_id.id)])
                    primary_template += "<select id='" + field.field_name + "' name='" + field.field_name + "'class='form-control' >"
                    for sel in sel_ids:
                        primary_template += "<option value='" + str(sel.value) + "' " + (" selected" if str(record_val) == sel.value else " ") + ">"
                        primary_template += sel.name
                        primary_template += "</option>"
                    primary_template += "</select>"
                
                # Date Field
                elif field.field_type == 'date':
                    primary_template += '<input type="date" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                elif field.field_type == 'char' and  field.field_name in ('in_time','out_time'):
                    primary_template += '<input type="time" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"    
                elif field.field_type == 'char':
                    primary_template += '<input type="text" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                elif field.field_type in ('integer','float','monetary'):
                    primary_template += '<input type="number" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
               
                else:
                    primary_template += '<input type="text" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"

                
                primary_template += "</div>"
        
        
        # ------------------------------------------
        # -------------Right Section Fields ----------------
        # ------------------------------------------
        for service in service_id:
            for field in hr_service_items.filtered(lambda line: line.display_option == 'right'):
                field_domain = []
                if record_sudo:
                    if field.field_id.sudo().ttype == 'many2one':
                        record_val = record_sudo[eval("'" + field.field_name + "'")].name
                    else:
                        record_val = str(record_sudo[eval("'" + field.field_name + "'")])
                        
                if field.is_required:
                    extra_template += "<div class='form-group col-12 s_website_form_required' data-type='char' data-name='" + field.field_name + "'>"
                else:
                    extra_template += "<div class='form-group col-12' data-type='char' data-name='" + field.field_name + "'>"
                extra_template += "<label class='s_website_form_label' style='width: 200px' for='" + field.field_name + "'>"
                extra_template += "<span class='s_website_form_label_content'>" + field.field_label + "</span>"
                extra_template += "</label>"
                
                # Many2one Field
                if field.field_type == 'many2one':
                    if field.field_model == 'ir.attachment':
                        extra_template += "<input type='file' class='form-control-file s_website_form_input' id='" + field.field_name + "' name='" + field.field_name + "' multiple='1' />"
                    else:
                        if field.field_domain:
                            field_domain = safe_eval.safe_eval(field.field_domain)
                            
                        m2o_id = request.env[field.field_model].sudo().search(field_domain)
                        
                        extra_template += "<select id='" + field.field_name + "' name='" + field.field_name + "'class='form-control' >"
                        for m in m2o_id:
                            extra_template += "<option value='" + str(m.id) + "' " + (" selected" if record_val == m.name else " ") + ">"
                            #template += "<t t-esc='t" + m.name + "'/>"
                            extra_template += m.name
                            extra_template += "</option>"
                        extra_template += "</select>"
                    
                # Selection field
                elif field.field_type == 'selection':
                    sel_ids = request.env['ir.model.fields.selection'].sudo().search([('field_id','=',field.field_id.id)])
                    extra_template += "<select id='" + field.field_name + "' name='" + field.field_name + "'class='form-control' >"
                    for sel in sel_ids:
                        extra_template += "<option value='" + str(sel.value) + "' " + (" 'selected'" if str(record_val) == sel.value else " ") + ">"
                        extra_template += sel.name
                        extra_template += "</option>"
                    extra_template += "</select>"
                
                # Date Field
                elif field.field_type == 'date':
                    extra_template += '<input type="date" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                elif field.field_type == 'datetime':
                    extra_template += '<input type="time" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"    
                elif field.field_type == 'char':
                    extra_template += '<input type="text" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                elif field.field_type in ('integer','float','monetary'):
                    extra_template += '<input type="number" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                else:
                    extra_template += '<input type="text" class="form-control s_website_form_input"' + 'name="' + field.field_name + '"' + ' id="' + field.field_name + '"' + 'value="' + record_val + '"' +  ('required="1"' if field.is_required else '') + ">"
                
                extra_template += "</div>"
            
        currency_ids = request.env['res.currency'].sudo().search([('active','=',True)])
        return {
            'currency_ids': currency_ids,
            'template_primary_fields': primary_template,
            'template_extra_fields': extra_template,
            'service_id': service_id,
            'record_id': record_id,
            'model_id': model_id,
            'edit_mode': edit_mode or 0,
        }
    
    @http.route(['/my/model/record/<int:service_id>/<int:model_id>/<int:record_id>/<int:edit_mode>'
                ], type='http', auth="user", website=True)        
    def portal_hr_service_record(self, service_id=False, model_id=False, record_id=False, edit_mode=False, **kw):
        return request.render("de_portal_hr_service.portal_service_record_form", self._prepare_service_record_page(service_id, model_id, record_id, edit_mode))
        
    
    @http.route('/my/model/record/submit', website=True, page=True, auth='public', csrf=False)
    def hr_service_record_submit(self, **kw):
        
        service_id = request.env['hr.service'].sudo().search([('id','=',(kw.get('service_id')))],limit=1)
        
        record_sudo = False
        parent_record_sudo = False
        record = False
        
        service_items = False
        
        model_id = (kw.get('model_id'))
        record_id = (kw.get('record_id'))
        edit_mode = (kw.get('edit_mode'))
        
        if model_id and record_id:
            model = request.env['ir.model'].sudo().search([('id','=',model_id)],limit=1)
            rs = request.env[model.model].sudo().search([('id','=',record_id)],limit=1)
        
        field_val = False
        
        line_item = request.env['hr.service.record.line'].sudo().search([('hr_service_id','=',service_id.id),('line_model_id','=',int(model_id))],limit=1)


        if service_id.header_model_id.id == int(model_id):
            service_items = service_id.hr_service_items
            if edit_mode == '1' or edit_mode == 1:
                record_sudo = request.env[service_id.header_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
                
        elif line_item.line_model_id: 
            service_items = line_item.hr_service_record_line_items 
            if edit_mode == '1' or edit_mode == 1:
                record_sudo = request.env[line_item.line_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
        
        user_id = request.env['res.users'].sudo().search([('id','=',http.request.env.context.get('uid'))],limit=1)
        
        vals = {}
        
        for field in service_items.filtered(lambda r: r.auto_populate):
            if field.auto_populate == 'user':
                vals.update({
                    field.field_name: user_id.id,
                })
            elif field.auto_populate == 'employee':
                vals.update({
                    field.field_name: user_id.employee_id.id,
                })
            elif field.auto_populate == 'partner':
                vals.update({
                    field.field_name: user_id.partner_id.id,
                })
        
        for field in service_items.filtered(lambda r: r.display_option in ['left','right']):
            if kw.get(field.field_name):
                field_val = kw.get(field.field_name)
                if field.field_type == 'many2one':
                    if field.field_model == 'ir.attachment':
                        data_file_name = kw.get(field.field_name).filename
                        data_file = kw.get(field.field_name)
                        attachment_id = request.env['ir.attachment'].sudo().create({
                            'name': data_file_name,
                            'type': 'binary',
                            'datas': base64.b64encode(data_file.read()),
                            'res_model': model.model,
                            'res_id': record_id,
                            'res_name': rs.name,
                        })
                        vals.update({
                            field.field_name: attachment_id.id,
                        })
                    else:                        
                        m2o_id = request.env[field.field_model].sudo().search([('id','=',int(field_val))],limit=1)
                        vals.update({
                            field.field_name: m2o_id.id,
                        })
                elif field.field_type == 'float':
                    vals.update({
                        field.field_name: float(kw.get(field.field_name))
                    })
                else:
                    vals.update({
                        field.field_name: kw.get(field.field_name)
                    })
            
        for field in service_items.filtered(lambda r: r.ref_field_id):
            if field.ref_field_id.ttype == 'many2one':
                ref_record_id = request.env[field.ref_field_id.relation].sudo().search([('id','=',int(kw.get(field.ref_field_id.name)))],limit=1)
                rel_field_id = request.env['ir.model.fields'].sudo().search([('model_id.model','=',field.ref_field_id.relation),('relation','=',field.field_model)],limit=1)
                vals.update({
                        field.field_name: ref_record_id[eval("'" + rel_field_id.name + "'")].id
                    })
                
            else :
                vals.update({
                        field.field_name: kw.get(field.ref_field_id.name)
                    })

        if service_id.header_model_id.id == int(model_id):
            if edit_mode == '0' or edit_mode == 0 or not edit_mode:
                record_sudo = request.env[service_id.header_model_id.model].sudo().create(vals)
            else:
                record_sudo.sudo().write(vals)
            record = record_sudo
                
        elif line_item.line_model_id.id == int(model_id):
            if edit_mode == '0' or edit_mode == 0 or not edit_mode:
                parent_record_sudo = request.env[service_id.header_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
                vals.update({
                    line_item.sudo().parent_relational_field_id.name: int(record_id),
                })
                record_sudo = request.env[line_item.line_model_id.model].sudo().create(vals)
                record = parent_record_sudo
            else:
                record = record_sudo[eval("'" + line_item.parent_relational_field_id.sudo().name + "'")]
                record_sudo.sudo().write(vals)
  
        return request.redirect('/my/model/record/%s/%s/%s' % (service_id.id,service_id.header_model_id.id, record.id))
    
    #delete record
    @http.route(['/my/model/record/<int:service_id>/<int:model_id>/<int:record_id>/delete'
                ], type='http', auth="user", website=True)        
    def portal_hr_service_record_delete(self, service_id=False, model_id=False, record_id=False, **kw):
        
        service_id = request.env['hr.service'].sudo().search([('id','=',int(service_id))],limit=1)
        record_sudo = False
        record = False
        line_item = request.env['hr.service.record.line'].sudo().search([('hr_service_id','=',service_id.id),('line_model_id','=',int(model_id))],limit=1)

        if service_id.header_model_id.id == int(model_id):
            record_sudo = request.env[service_id.header_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
            record = request.env[service_id.header_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
        elif line_item.line_model_id.id == int(model_id):
            record_sudo = request.env[line_item.line_model_id.model].sudo().search([('id','=',int(record_id))],limit=1)
            record = record_sudo[eval("'" + line_item.parent_relational_field_id.sudo().name + "'")]
                
        record_sudo.sudo().unlink()
        return request.redirect('/my/model/record/%s/%s/%s' % (service_id.id,model_id, record.id))
