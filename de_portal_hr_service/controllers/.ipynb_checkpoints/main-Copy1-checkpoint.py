# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from operator import itemgetter

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        EntryOrder = request.env['account.custom.entry']
        
        if 'entry_count' in counters:
            values['entry_count'] = EntryOrder.search_count(self._prepare_entries_domain(partner)) \
                if EntryOrder.check_access_rights('read', raise_exception=False) else 0
            values['partner'] = partner
        
        return values

    def _prepare_entries_domain(self, partner):
        return ['|',
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', '=', [partner.id])
            
        ]
    
    
    # Entry Orders
    #

    def _get_entry_searchbar_sortings(self):
        return {
            'date': {'label': _('Order Date'), 'order': 'date_entry desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }
    
        
    def _get_portal_my_entries_content(self,type_id,entries):
        template = ''
        # Dynamic Header
        custom_entry_type_id = request.env['account.custom.entry.type'].sudo().search([('id','=',type_id)],limit=1)
        
        template += "<t class='col-lg-6 col-md-4 mb16 mt32'>"
        template +=  "<a href='/my/entry/new/" + str(custom_entry_type_id.id) + "' class='btn btn-primary pull-left' >Create New " + str(custom_entry_type_id.name) + "</a>"
        template += "</t>"
        
        attachment_id = request.env['ir.attachment'].search([('res_model','=','account.custom.entry.type')],limit=1)
        
        template += "<t class='col-lg-6 col-md-4 mb16 mt32'>"
        template +=  "<a href='" + str(attachment_id.url) + "' target='_blank' class='pull-right' >Download Template " + str(custom_entry_type_id.name) + "</a>"
        template += "</t>"
        
        template += "<table class='table rounded mb-0 bg-white o_portal_my_doc_table'>"
        
        template += "<thead class='bg-100'>"
        for type in custom_entry_type_id:
            for label in type.custom_entry_header_field_ids:
                template += "<th>" + label.field_label + "</th>"
        template += "</thead>"
        
        #template = ''
        
        #Dynamic Contents
        counter = 0
        template += "<tbody class='entry_tbody'>"
        m2o_obj = False
        domain = []
        for line in entries:
            counter += 1
            if counter % 2 == 0:
                template += "<tr class='bg-200'>"
            else:
                template += "<tr>"
                
            for f in line.custom_entry_type_id.custom_entry_header_field_ids:    
                template += "<td>"
                if f.field_name == 'display_name':
                    template += "<a href='/my/entries/" + str(line.id) + "?'>" + str(line[eval("'" + f.field_name + "'")]) + "</a>"
                elif f.field_type == 'many2one':
                    #line[eval("'" + f.field_name + "'")]._apply_ir_rules('read')
                    template += str(line[eval("'" + f.field_name + "'")].sudo().name)
                    #template += str(line[eval("'" + f.field_name + "'")].name) \
                    #    if line[eval("'" + f.field_name + "'")].check_access_rights('read', raise_exception=False) else 0

                elif f.field_type == 'selection':
                    sel_id = request.env['ir.model.fields.selection'].sudo().search([('field_id','=',f.field_id.id),('value','=',line[eval("'" + f.field_name + "'")])],limit=1)
                    if sel_id:
                        template += str(sel_id.name)
                else:
                    template += str(line[eval("'" + f.field_name + "'")])
                    
                template += "</td>"
            template += "<td class='text-left'><a href='/web/content/" + str(line.data_file_id.id) + "?download=true' title='Dowload'><i class='fa fa-download'></i></a></td>"
            
            template += "<td>"
            if line.is_portal_editable:
                template += "<a href='/my/entry/update/" + str(line.id) + "'><i class='fa fa-upload'  style='color:red;'></i></a>"
            template += "</td>"

            template += "</tr>"
                
        template += "</tbody>"
        template += "</table>"
        return template
    
    
    # ------------------------------------------------------------
    # My types
    # ------------------------------------------------------------
    def _type_get_page_view_values(self, type, access_token, **kwargs):
        values = {
            'page_name': 'type',
            'type': type,
        }
        return self._get_page_view_values(type, access_token, values, 'my_types_history', False, **kwargs)

    @http.route(['/my/types', '/my/types/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_types(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Type = request.env['account.custom.entry.type']
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # types count
        type_count = Type.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/types",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=type_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        types = Type.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_types_history'] = types.ids[:100]
        
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'types': types,
            'page_name': 'type',
            'default_url': '/my/types',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_custom_journal_entry_web.portal_my_entry_types", values)
    
    @http.route(['/my/type/<int:type_id>'], type='http', auth="public", website=True)
    def portal_my_type(self, type_id=None, access_token=None, **kw):
        try:
            type_sudo = self._document_check_access('account.custom.entry.type', type_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._type_get_page_view_values(type_sudo, access_token, **kw)
        return request.render("de_custom_journal_entry_web.portal_my_entry_types", values)
    
    
    @http.route(['/my/entries', '/my/entries/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_entries(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Title'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id, custom_entry_type_id'},
            'type': {'label': _('Type'), 'order': 'custom_entry_type_id, stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'stage': {'input': 'stage', 'label': _('Search in Stages')},
            'type': {'input': 'type', 'label': _('Search in Type')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'type': {'input': 'type', 'label': _('Type')},
            'stage': {'input': 'stage', 'label': _('Stage')},
        }

        # extends filterby criteria with project the customer has access to
        types = request.env['account.custom.entry.type'].search([])
        for type in types:
            searchbar_filters.update({
                str(type.id): {'label': type.name, 'domain': [('custom_entry_type_id', '=', type.id)]}
            })

        # extends filterby criteria with project (criteria name is the project id)
        # Note: portal users can't view projects they don't follow
        type_groups = request.env['account.custom.entry'].read_group([('custom_entry_type_id', 'not in', types.ids)],
                                                                ['custom_entry_type_id'], ['custom_entry_type_id'])
        for group in type_groups:
            proj_id = group['custom_entry_type_id'][0] if group['custom_entry_type_id'] else False
            proj_name = group['custom_entry_type_id'][1] if group['custom_entry_type_id'] else _('Others')
            searchbar_filters.update({
                str(proj_id): {'label': proj_name, 'domain': [('custom_entry_type_id', '=', proj_id)]}
            })

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']

        # default group by value
        if not groupby:
            groupby = 'type'

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            if search_in in ('stage', 'all'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            if search_in in ('project', 'all'):
                search_domain = OR([search_domain, [('project_id', 'ilike', search)]])
            domain += search_domain

        # task count
        entry_count = request.env['account.custom.entry'].search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/entries",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'groupby': groupby, 'search_in': search_in, 'search': search},
            total=entry_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        if groupby == 'project':
            order = "project_id, %s" % order  # force sort on project first to group by project in view
        elif groupby == 'stage':
            order = "stage_id, %s" % order  # force sort on stage first to group by stage in view

        entries = request.env['account.custom.entry'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tasks_history'] = entries.ids[:100]

        if groupby == 'type':
            grouped_entries = [request.env['account.custom.entry'].concat(*g) for k, g in groupbyelem(entries, itemgetter('custom_entry_type_id'))]
        elif groupby == 'stage':
            grouped_entries = [request.env['account.custom.entry'].concat(*g) for k, g in groupbyelem(entries, itemgetter('stage_id'))]
        else:
            grouped_entries = [entries]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_entries': grouped_entries,
            'page_name': 'task',
            'default_url': '/my/entries',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        
        #type_id = request.env['account.custom.entry.type'].sudo().search([('id','=',type_id)],limit=1)
        type_id = 1
        values.update({
            'portal_my_entries_content': self._get_portal_my_entries_content(type_id,entries)           
        })
        
        
        values.update({
            'type_id': type_id,
        })
        
        return request.render('de_custom_journal_entry_web.portal_my_entries', values)
    
    # -------------------------------------
    # older types
    # -------------------------------------
    @http.route(['/my/types1', 
                 '/my/types1/<int:type_id>',
                 '/my/types1/page/<int:page>'
                ], type='http', auth="user", website=True)
    def portal_my_types1(self, type_id=False, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        EntryOrder = request.env['account.custom.entry']

        domain = self._prepare_entries_domain(partner)

        searchbar_sortings = self._get_entry_searchbar_sortings()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        #if date_begin and date_end:
        #    domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        domain += [('custom_entry_type_id','=',type_id)]

        # count for pager
        
        entry_count = EntryOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/types1",
            #url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=entry_count,
            page=page,
            step=5, #self._items_per_page
        )
        # search the count to display, according to the pager data
        entries = EntryOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_entries_history'] = entries.ids[:100]

        values.update({
            'date': date_begin,
            'entries': entries.sudo(),
            'page_name': 'type',
            'pager': pager,
            'default_url': '/my/types1',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        #type_id = request.env['account.custom.entry.type'].sudo().search([('id','=',entries.custom_entry_type_id.id)],limit=1)
        
        
        values.update({
            'portal_my_entries_content': self._get_portal_my_entries_content(type_id,entries)           
        })
        
        type_id = request.env['account.custom.entry.type'].sudo().search([('id','=',type_id)],limit=1)
        values.update({
            'type_id': type_id,
        })
        
        return request.render("de_custom_journal_entry_web.portal_my_entries", values)
    
    
    @http.route(['/my/entries1', '/my/entries1/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_entries1(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        EntryOrder = request.env['account.custom.entry']

        domain = self._prepare_entries_domain(partner)

        searchbar_sortings = self._get_entry_searchbar_sortings()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        entry_count = EntryOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/entries1",
            #url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=entry_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        entries = EntryOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_entries_history'] = entries.ids[:100]

        values.update({
            'date': date_begin,
            'entries': entries.sudo(),
            'page_name': 'entry',
            'pager': pager,
            'default_url': '/my/entries1',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        type_id = request.env['account.custom.entry.type'].sudo().search([('id','=',entries.custom_entry_type_id.id)],limit=1)
        values.update({
            'portal_my_entries_content': self._get_portal_my_entries_content(type_id.id,entries)           
        })
        
        values.update({
            'type_id': type_id
        })
        return request.render("de_custom_journal_entry_web.portal_my_entries", values)
    

    @http.route(['/my/entries/<int:entry_id>'], type='http', auth="public", website=True)
    def portal_entry_page(self, entry_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            entry_sudo = self._document_check_access('account.custom.entry', entry_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=entry_sudo, report_type=report_type, report_ref='sale.action_report_saleorder', download=download)

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if entry_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            #session_obj_date = request.session.get('view_quote_%s' % entry_sudo.id)
            #if session_obj_date != now and request.env.user.share and access_token:
            #    request.session['view_quote_%s' % entry_sudo.id] = now
            #    body = _('Quotation viewed by customer %s', entry_sudo.partner_id.name)
            #    _message_post_helper(
            #        "account.custom.entry",
            #        entry_sudo.id,
            #        body,
            #        token=entry_sudo.access_token,
            #        message_type="notification",
            #        subtype_xmlid="mail.mt_note",
            #        partner_ids=entry_sudo.user_id.sudo().partner_id.ids,
            #    )

        values = {
            'entry_order': entry_sudo,
            'message': message,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': entry_sudo.partner_id.id,
            'report_type': 'html',
        }
        if entry_sudo.company_id:
            values['res_company'] = entry_sudo.company_id

            values.update({
                'amount': entry_sudo.amount_total,
                'currency': entry_sudo.currency_id,
                'partner_id': entry_sudo.partner_id.id,
                #'access_token': entry_sudo.access_token,
            })

        history = request.session.get('my_entries_history', [])
        values.update(get_records_pager(history, entry_sudo))

        values.update({
            'portal_entry_dyanmic_page_template': self.portal_entry_dyanmic_page_template(entry_sudo),
        })
        
        
        return request.render('de_custom_journal_entry_web.entry_order_portal_template', values)
    
    def portal_entry_dyanmic_page_template(self,entry_id):
        # TEMPORARY RETURNS CONSTANT FOR DEVELOPMENT PURPOSE
        m2m_ids = False
        fields = ''
        template = ''
        template += "<div id='informations'>"
        template += "<div class='row' id='so_date'>"
        for header in entry_id.custom_entry_type_id.custom_entry_header_field_ids:
            template += "<div class='mb-3 col-6'>"
            template += "<strong>" + header.field_label + ": </strong>"
            
            if header.field_type == 'many2one':
                template += "<span>" + str(entry_id[eval("'" + header.field_name + "'")].name) \
                    if entry_id[eval("'" + header.field_name + "'")].check_access_rights('read', raise_exception=False) else 0 \
                + "</span>"
            elif header.field_type == 'many2many':
                m2m_ids = request.env[header.field_model].sudo().search([('id','in',entry_id[eval("'" + header.field_name + "'")].ids)])
                    #if m2m_ids.check_access_rights('read', raise_exception=False) else 0
                m2m_text = ''
                for m2m in m2m_ids:
                    m2m_text += m2m.name + ','
                template += "<span>" + m2m_text[:-1] + "</span>"
            elif header.field_type == 'selection':
                sel_id = request.env['ir.model.fields.selection'].sudo().search([('field_id','=',header.field_id.id),('value','=',entry_id[eval("'" + header.field_name + "'")])],limit=1)
                if sel_id:
                    template += "<span>" + str(sel_id.name) + "</span>"
            else:
                template += "<span>" + str(entry_id[eval("'" + header.field_name + "'")]) + "</span>"
                    
                    
            template += "</div>"
        template += "</div>"
        template += "</div>"
        
        # line items
        template += "<section id='details' style='page-break-inside: auto; overflow:scroll;' class='mt32'>"
        template += "<table class='table table-sm'>"
        template += "<thead class='bg-100'>"
        for label in entry_id.custom_entry_type_id.custom_entry_import_field_ids:
            template += "<th>" + label.field_label + "</th>"
        template += "</thead>"
        
        counter = 0
        m2m_text = ''
        
        template += "<tbody class='sale_tbody'>"
        for line in entry_id.custom_entry_line:
            counter += 1
            if counter % 2 == 0:
                template += "<tr class='bg-200'>"
            else:
                template += "<tr>"
                
            for f in entry_id.custom_entry_type_id.custom_entry_import_field_ids:    
                fields += f.field_name + ','
                template += "<td>"
                #template += eval("'" + f.field_name + "'")
                if f.field_type == 'many2one':
                    template += str(line[eval("'" + f.field_name + "'")].name) \
                        if line[eval("'" + f.field_name + "'")].check_access_rights('read', raise_exception=False) else 0

                elif f.field_type == 'many2many':
                    m2m_ids = request.env[f.field_model].sudo().search([('id','in',line[eval("'" + f.field_name + "'")].ids)])
                    #if m2m_ids.check_access_rights('read', raise_exception=False) else 0
                    m2m_text = ''
                    for m2m in m2m_ids:
                        m2m_text += m2m.name + ','
                    template += m2m_text[:-1]
                    #template += str(line[eval("'" + f.field_name + "'")].ids)
                elif f.field_type == 'selection':
                    sel_id = request.env['ir.model.fields.selection'].sudo().search([('field_id','=',f.field_id.id),('value','=',line[eval("'" + f.field_name + "'")])],limit=1)
                    if sel_id:
                        template += str(sel_id.name)
                else:
                    template += str(line[eval("'" + f.field_name + "'")])
                template += "</td>"
                
            template += "</tr>"
                
        fields = fields[:-1]
        template += "</tbody></table></section>"
        #template += fields
        
        #query = """
        #select """ + fields + """
        #from account_custom_entry_line where custom_entry_id = """ + str(entry_id.id) + """
        #"""
        
        
        #request.cr.execute(query)
        #rs_line = request.cr.fetchall()
        #rs_line = request.cr.dictfetchall()

        #rs_line = self._cr.dictfetchall()
        #for rs in rs_line:
        #    for f in entry_id.custom_entry_type_id.custom_entry_import_field_ids:
        #        template += 'product=' + str(rs[f.field_name])
        
        #template += query
        
        
        #template += "<h2>Lines</h2>"
        #for line in entry_id.custom_entry_line:
            
            #template += "<t t-foreach='entry_order.custom_entry_line' t-as='line'>"
            #template += "<span t-field='line.product_id.name'/>"
            #template += "</t>"
            #template += "<h3>" + line.product_id.name + "</h3>"
        return template