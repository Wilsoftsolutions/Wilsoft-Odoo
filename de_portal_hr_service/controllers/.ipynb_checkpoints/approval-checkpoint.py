# # -*- coding: utf-8 -*-

from . import config
from . import update
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError
from collections import OrderedDict
from operator import itemgetter
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR

def approval_page_content(flag = 0):
    partner = request.env['res.partner'].sudo().search([])
    category = request.env['category.approval'].sudo().search([])
    return {
        'approval_data': category,
        'oweners_res_partner' : partner,
        'success_flag' : flag,
    }

def paging(data, flag1 = 0, flag2 = 0):        
    if flag1 == 1:
        return config.list12
    elif flag2 == 1:
        config.list12.clear()
    else:
        k = []
        for rec in data:
            for ids in rec:
                config.list12.append(ids.id)        
        
class CreateApproval(http.Controller):
    @http.route('/approval/create/',type="http", website=True, auth='user')
    def approvals_create_template(self, **kw):
        return request.render("de_portal_hr_service.create_approval",approval_page_content()) 
    



class CustomerPortal(CustomerPortal):
    
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'approval_count' in counters:
            values['approval_count'] = request.env['hr.approval.request'].search_count([])
        
        return values
    
    @http.route(['/app/approval/accept/<int:approval_id>'], type='http', auth="public", website=True)
    def approval_accept(self,approval_id ,**kw):
        id=approval_id
        recrd = request.env['hr.approval.request'].sudo().browse(id)
        recrd.action_approve()
        approvals_page = CustomerPortal()
        return request.redirect('/my/approvals')
        #return request.render("de_portal_hr_service.approval_submited", {})
        
    @http.route(['/request/refuse/<int:approval_id>'], type='http', auth="public", website=True)
    def action_approval_reject(self,approval_id ,**kw):
        id=approval_id
        recrd = request.env['hr.approval.request'].sudo().browse(id)
        recrd.action_refuse()
        approvals_page = CustomerPortal()
        return request.redirect('/my/approvals')
        #return request.render("de_portal_hr_service.approval_refused", {})
        
    @http.route(['/app/approval/approve/<int:approval_id>'], type='http', auth="public", website=True)
    def approval(self,approval_id , access_token=None, **kw):
        id=approval_id
        record = request.env['hr.approval.request'].sudo().browse(id)

        record.action_approve()
        try:
            approval_sudo = self._document_check_access('hr.approval.request', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._approval_get_page_view_values(approval_sudo, access_token,**kw)
        return request.redirect('/my/approvals') 
        #return request.render("de_portal_hr_service.approval_submited", {})
        
        
    @http.route(['/app/approval/refuse/<int:approval_id>'], type='http', auth="public", website=True)
    def refuse(self,approval_id , access_token=None, **kw):
        id=approval_id
        recrd = request.env['hr.approval.request'].sudo().browse(id)

        recrd.action_refuse()
        try:
            approval_sudo = self._document_check_access('hr.approval.request', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._approval_get_page_view_values(approval_sudo, access_token,**kw) 
        return request.redirect('/my/approvals')
        #return request.render("de_portal_hr_service.approval_refused", {})
    
    
    
    # ------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------
    def _approval_get_page_view_values(self, approval, access_token, **kwargs):
        values = {
            'page_name': 'approval',
            'approval': approval,
        }
        return self._get_page_view_values(approval, access_token, values, 'my_approval_history', False, **kwargs)

    @http.route(['/my/approvals', '/my/approvals/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_approvals(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        approval = request.env['hr.approval.request']
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

        # approval count
        approval_count = approval.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/approvals",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=approval_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        approvals = approval.sudo().search(domain, order=order, limit=10000, offset=pager['offset'])
        request.session['my_approvals_history'] = approvals.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_approvals': approvals,
            'page_name': 'approval',
            'default_url': '/my/approvals',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_portal_hr_service.portal_my_approvals", values)

    @http.route(['/my/approval/<int:approval_id>'], type='http', auth="public", website=True)
    def portal_my_approval(self, approval_id=None, access_token=None, **kw):
        try:
            approval_sudo = request.env['hr.approval.request'].sudo().search([('id','=',approval_id)]) 
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._approval_get_page_view_values(approval_sudo, access_token, **kw)
        return request.render("de_portal_hr_service.portal_my_approval", values)

    
    
    
    
