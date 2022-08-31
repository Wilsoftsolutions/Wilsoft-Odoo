# # -*- coding: utf-8 -*-
from . import config
from . import update
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models,  _, SUPERUSER_ID
from odoo.osv import expression
from odoo.exceptions import UserError
from collections import OrderedDict
from operator import itemgetter
from datetime import datetime , date
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR
from datetime import date, datetime, timedelta
from odoo import exceptions
from dateutil.relativedelta import relativedelta
import base64
import binascii
import json



def timeoff_page_content(flag = 0):
    leave_type = request.env['hr.leave.type'].sudo().search([('is_publish','=', True)])
    employees = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
    leave_type_list = []
    allocation_list = []
    leave_allocation = request.env['hr.leave.allocation'].sudo().search([('employee_id.user_id', '=', http.request.env.context.get('uid') ),('state','=','validate'),('fiscal_year','=', fields.date.today().year)])
    for allocate in leave_allocation:
        leave_type_list.append(allocate.holiday_status_id.id)    
    uniq_leave_allocation = set(leave_type_list)
    for uniq_allocate in uniq_leave_allocation:
        uniq_allocation_leave = request.env['hr.leave.allocation'].sudo().search([('holiday_status_id','=',uniq_allocate),('employee_id.user_id', '=', http.request.env.context.get('uid')), ('state','=','validate')], limit=1)
        uniq_leave_taken = request.env['hr.leave'].sudo().search([('holiday_status_id','=',uniq_allocate),('employee_id.user_id', '=', http.request.env.context.get('uid')),('state','in', ('validate', 'confirm'))])
        leave_taken_count = 0
        for leave_count in uniq_leave_taken:
            leave_taken_count += leave_count.number_of_days
        if uniq_allocation_leave.max_leaves > 0.0:
            allocation_list.append({
                'alloc_id': uniq_allocation_leave.id,
                'leave_categ': uniq_allocation_leave.holiday_status_id.name,
                'leave_max': round(uniq_allocation_leave.max_leaves,2),
                'leave_taken': round(leave_taken_count,2),
                'balance': round((uniq_allocation_leave.max_leaves - leave_taken_count),2),
            })
    company_info = request.env['res.users'].sudo().search([('id','=',http.request.env.context.get('uid'))])
    managers = employees.parent_id.name
    employee_name = employees
    req = request.env['hr.leave.type'].sudo().search([('fiscal_year','=',fields.date.today().year),('company_id','=',employees.company_id.id)], limit=1)
    leave_allocationaa = request.env['hr.leave.allocation'].sudo().search([('employee_id.user_id', '=', http.request.env.context.get('uid') ),('state','=','validate'),('fiscal_year','=', fields.date.today().year)], limit=1)
    return {
        'leave_type' : leave_type,
        'allocation_list': allocation_list,
        'employees' : employees,
        'employee_name': employee_name,
        'managers': managers,
        'leave_allocation': leave_allocation,
        'success_flag' : flag,
        'company_info' : company_info,
        'req_date_from': leave_allocationaa.date_from,
        'req_date_to': leave_allocationaa.date_to,
    }
   
    
def timeoff_page_exception( e):  
    return {
        'e': e
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
 
    
        
class CreateTimeOff(http.Controller):

    @http.route('/timeoff/create/',type="http", website=True, auth='user')
    def timeoff_create_template(self, **kw):
        return request.render("ws_portal_leave.leave_template",timeoff_page_content()) 
    
    
    @http.route('/leave/ledger/print/',type="http", website=True, auth='user')
    def action_print_leave_ledger(self, **kw):
        return request.render("ws_portal_leave.print_leave_ledger_report", timeoff_page_content())
    
    
    @http.route('/my/timeoff/save', type="http", auth="public", website=True)
    def leave_submit_forms(self, **kw):
        if kw.get('leave_category_id') == 'day':
            date_start1 = datetime.strptime(kw.get('date_start') , '%Y-%m-%d')
            date_end1 =  datetime.strptime(kw.get('date_end') , '%Y-%m-%d')
            days = (date_end1 - date_start1).days
            date_weekday = datetime.strptime(kw.get('date_start') , '%Y-%m-%d')
            weekday = date_weekday.weekday()
            hours_from = 8
            hours_to = 16
            employee_schedule = request.env['hr.employee'].sudo().search([('id','=', int(kw.get('employee_id')))])
            for emp_schedule in employee_schedule.resource_calendar_id.attendance_ids:
                hours_from = emp_schedule.hour_from
                hours_to = emp_schedule.hour_to               
                if emp_schedule.dayofweek == weekday:
                    hours_from = emp_schedule.hour_from
                    hours_to = emp_schedule.hour_to       
            
            date_start =  date_start1 + relativedelta(hours =+ hours_from) 
            date_end = date_end1 + relativedelta(hours =+ hours_to)
            if date_end < date_start:
                hours_from = 8
                hours_to = 16
                date_start =  date_start1 + relativedelta(hours =+ hours_from) 
                date_end = date_end1 + relativedelta(hours =+ hours_to)
            if kw.get('attachment'):
                Attachments = request.env['ir.attachment']
                name = kw.get('attachment').filename
                file = kw.get('attachment')
                attachment_id = Attachments.sudo().create({
                'name': name,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                 })
                timeoff_val = {
                    'holiday_status_id': int(kw.get('leave_type_id')),
                    'employee_id': int(kw.get('employee_id')),            
                    'date_from':date_start,
                    'date_to': date_end,
                    'leave_category': kw.get('leave_category_id'),
                    'attachment_id': [(4, attachment_id.id)],
                    'request_date_from':str(kw.get('date_start')),
                    'request_date_to': str(kw.get('date_end')),
                    'name':kw.get('description'),
                }
                record = request.env['hr.leave'].sudo().create(timeoff_val)
                
                record.update({
                     'date_from':date_start - relativedelta(hours =+ 5),
                     'date_to': date_end - relativedelta(hours =+ 5),
                })
                
            else:
                timeoff_val = {
                    'holiday_status_id': int(kw.get('leave_type_id')),
                    'employee_id': int(kw.get('employee_id')),            
                    'date_from':date_start,
                    'date_to': date_end,
                    'leave_category': kw.get('leave_category_id'),
                    'request_date_from':str(kw.get('date_start')),
                    'request_date_to': str(kw.get('date_end')),
                    'name':kw.get('description'),
                }
                record = request.env['hr.leave'].sudo().create(timeoff_val)
                
                record.update({
                     'date_from':date_start - relativedelta(hours =+ 5),
                     'date_to': date_end - relativedelta(hours =+ 5),
                })
                
            if kw.get('date_start') and kw.get('date_end'):
                dddate_from = datetime.strptime(str(kw.get('date_start')), '%Y-%m-%d')
                dddate_to = datetime.strptime(str(kw.get('date_end')), '%Y-%m-%d')
                dddelta = dddate_to - dddate_from
                
                tot_rest_days = 0
                gazetted_days_count = 0
                COUNT_1 = 0
                shift = employee_schedule.resource_calendar_id
                
                if not shift:
                    shift = request.env['resource.calendar'].sudo().search([('company_id','=',employee_schedule.company_id.id)], limit=1)
                    
                for gazetted_day in shift.global_leave_ids:
                        gazetted_date_from = gazetted_day.date_from + relativedelta(hours=+5)
                        gazetted_date_to = gazetted_day.date_to + relativedelta(hours=+5)
                        if str(dddate_from.strftime('%y-%m-%d')) >= str(gazetted_date_from.strftime('%y-%m-%d')) and str(dddate_to.strftime('%y-%m-%d')) <= str(gazetted_date_to.strftime('%y-%m-%d')):
                            
                            gazetted_days_count += 1 
                                                    
                if dddelta.days == 0.0:
                    record.update({
                    'number_of_days': 1
                    }) 
                record.action_confirm_data()    
        if kw.get('leave_category_id') == 'half_day':
            day_half = kw.get('leave_half_day')
            date_from = kw.get('half_day_date') 
            date_start = kw.get('half_day_date') 
            date_end =  kw.get('half_day_date') 
            date_weekday = datetime.strptime(kw.get('half_day_date') , '%Y-%m-%d')
            weekday = date_weekday.weekday()
            employee11 = request.env['hr.employee'].sudo().search([('id','=', int(kw.get('employee_id')))], limit=1)
            hour_to =  str((employee11.resource_calendar_id.hours_per_day/2))
            date_start1 = datetime.strptime(kw.get('half_day_date') , '%Y-%m-%d')
            date_start2 = datetime.strptime(kw.get('half_day_date') , '%Y-%m-%d')
            hours_from = 8
            hours_to = 16
            employee_schedule = request.env['hr.employee'].sudo().search([('id','=', int(kw.get('employee_id')))])
            for emp_schedule in employee_schedule.resource_calendar_id.attendance_ids:
                hours_from = emp_schedule.hour_from
                hours_to = emp_schedule.hour_to               
                if emp_schedule.dayofweek == weekday:
                    hours_from = emp_schedule.hour_from
                    hours_to = emp_schedule.hour_to       
            date_start =  date_start1 + relativedelta(hours =+ hours_from) 
            date_end = date_start2 + relativedelta(hours =+ hours_to)  
            day_period = 'am'
            if day_half == 'Morning':
                day_period = 'am'
                date_end = date_end - relativedelta(hours =+ float(employee_schedule.resource_calendar_id.hours_per_day)/2)     
                
            elif day_half == 'Evening':
                day_period = 'pm'
                date_start =  date_start + relativedelta(hours =+ float(employee_schedule.resource_calendar_id.hours_per_day)/2) 
            leave_period_half = 'first_half'
            request_date_from_period = 'am'
            if day_half == 'Evening':
                leave_period_half = 'second_half' 
                request_date_from_period = 'pm'  
            if date_end < date_start:
                hours_from = 8
                hours_to = 12
                date_start =  date_start1 + relativedelta(hours =+ hours_from) 
                date_end = date_start2 + relativedelta(hours =+ hours_to)   
            timeoff_val = {
                'holiday_status_id': int(kw.get('leave_type_id')),
                'employee_id': int(kw.get('employee_id')),            
                'date_from':date_start - relativedelta(hours =+ 5),
                'date_to': date_end - relativedelta(hours =+ 5),
                'leave_period_half': leave_period_half,  
                'request_unit_half': True,
                'request_date_from_period': request_date_from_period,
                'leave_category': kw.get('leave_category_id'),
                'leave_category': kw.get('leave_category_id'),
                'request_date_from':kw.get('half_day_date'),
                'request_date_to': kw.get('half_day_date'),
                'number_of_days': 0.50 ,
                'name':kw.get('description'),
            }
            record = request.env['hr.leave'].sudo().create(timeoff_val)
            record.update({
                'number_of_days': 0.50,
                'date_from':date_start - relativedelta(hours =+ 5),
                'date_to': date_end - relativedelta(hours =+ 5),
            })
            record.update({
                'number_of_days': 0.50,

            })
            record.action_confirm_data()
            if kw.get('attachment'):
                Attachments = request.env['ir.attachment']
                name = kw.get('attachment').filename
                file = kw.get('attachment')
                attachment_id = Attachments.create({
                'name': name,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                 })
                record.update({
                   'attachment_id': [(4, attachment_id.id)],
                 })
        
        attachment = 0
        if kw.get('leave_category_id') == 'hours': 
            hour_from = kw.get('time_from') 
            employee11 = request.env['hr.employee'].sudo().search([('id','=', int(kw.get('employee_id')))], limit=1)
            hour_to =  str(float(kw.get('time_from').replace(":",".")) + (employee11.resource_calendar_id.hours_per_day/4))
            date_start1 = datetime.strptime(kw.get('hours_date') , '%Y-%m-%d')
            short_leave_start_obj = datetime.strptime(kw.get('time_from'), '%H:%M')
            date_start =  date_start1 + relativedelta(hours =+ short_leave_start_obj.hour,minutes=short_leave_start_obj.minute)       
            short_leave_hours = 2
            if  employee11.resource_calendar_id:
                short_leave_hours = employee11.resource_calendar_id.hours_per_day/4          
            date_end =  date_start + relativedelta(hours =+ float(short_leave_hours))
            timeoff_val = {
                'holiday_status_id': int(kw.get('leave_type_id')),
                'employee_id': int(kw.get('employee_id')),            
                'date_from':date_start,
                'short_start_time': kw.get('time_from').replace(":","."),
                'date_to': date_end,
                'leave_category': kw.get('leave_category_id'),
                'request_date_from':kw.get('hours_date'),
                'request_date_to': kw.get('hours_date'),
                'number_of_days': 0.25 ,
                'name':kw.get('description'),
            }
            record = request.env['hr.leave'].sudo().create(timeoff_val)
            record.update({
                'number_of_days': 0.25 ,
                'date_from':date_start - relativedelta(hours =+ 5),
                'date_to': date_end - relativedelta(hours =+ 5),
            })
            record.update({
                'number_of_days': 0.25 ,

            })
            record.action_confirm_data()
            if kw.get('attachment'):
                Attachments = request.env['ir.attachment']
                name = kw.get('attachment').filename
                file = kw.get('attachment')
                attachment_id = Attachments.create({
                'name': name,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                })
                record.update({
                   'attachment_id': [(4, attachment_id.id)],
                 })

        return request.render("ws_portal_leave.leave_submited", {}, timeoff_page_content())
  

    
    
    
class CustomerPortal(CustomerPortal):
    
    
    def _show_leave_report_portal(self, model, report_type, employee, start_date, end_date, report_ref, download=False):
        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s", report_type))

        report_sudo = request.env.ref(report_ref).with_user(SUPERUSER_ID)

        if not isinstance(report_sudo, type(request.env['ir.actions.report'])):
            raise UserError(_("%s is not the reference of a report", report_ref))

        if hasattr(model, 'company_id'):
            report_sudo = report_sudo.with_company(model.company_id)

        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(report_sudo, method_name)([model], data={'report_type': report_type,'employee':employee,'start_date':start_date,'end_date':end_date})[0]
        reporthttpheaders = [
            ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
            ('Content-Length', len(report)),
        ]
        if report_type == 'pdf' and download:
            filename = "%s.pdf" % (re.sub('\W+', '-', model._get_report_base_filename()))
            reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
        return request.make_response(report, headers=reporthttpheaders)


    
    @http.route('/leave/ledger/print/report',type="http", website=True,download=False, auth='user')
    def action_print_leave_ledger_report(self, **kw):
        report_type='pdf'
        order_sudo = 'hr.leave'
        download = False
        employee = request.env['hr.employee'].search([('id','=',int(kw.get('employee_id')))]).id
        start_date = kw.get('date_from')
        end_date = kw.get('date_to')
        return self._show_leave_report_portal(model=order_sudo, report_type=report_type,employee=employee, start_date=start_date, end_date=end_date, report_ref='ws_portal_leave.open_leave_ledger_wizard_action_portal', download=download)
    
    
    @http.route(['/hr/leave/cancel/<int:approval_id>'], type='http', auth="public", website=True)
    def approval_reject(self,approval_id ,**kw):
        id=approval_id
        recrd = request.env['hr.leave'].sudo().browse(id)
        recrd.action_cancel()
        approvals_page = CustomerPortal()
        return request.render("ws_portal_leave.leave_cancel", {})
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'timeoff_count' in counters:
            values['timeoff_count'] = request.env['hr.leave'].search_count([('employee_id.user_id', '=', http.request.env.context.get('uid') )])
        return values
  
    def _timeoff_get_page_view_values(self,timeoff, next_id = 0,pre_id= 0, timeoff_user_flag = 0, access_token = None, **kwargs):
        company_info = request.env['res.users'].search([('id','=',http.request.env.context.get('uid'))])
        values = {
            'page_name': 'timeoff',
            'timeoff': timeoff,
            'current_date':fields.date.today(),
            'timeoff_user_flag':timeoff_user_flag,
            'next_id' : next_id,
            'company_info': company_info,
            'pre_id' : pre_id,
        }
        return self._get_page_view_values(timeoff, access_token, values, 'my_timeoff_history', False, **kwargs)
    

    @http.route(['/my/timeoffs', '/my/timeoff/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timeoffs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'employee_id': {'label': _('Employee'), 'order': 'employee_id desc' },
            'update': {'label': _('Last Update'), 'order': 'write_date desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'cancel','confirm','refuse','validate1','validate'])]},
            'draft': {'label': _('To Submit'), 'domain': [('state', '=', 'draft')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},  
            'confirm': {'label': _('To Approve'), 'domain': [('state', '=', 'confirm')]},
            'refuse': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]}, 
            'validate1': {'label': _('Second Approved'), 'domain': [('state', '=', 'validate1')]},
            'validate': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
        }
        searchbar_inputs = { 
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'holiday_status_id': {'input': 'holiday_status_id', 'label': _('Search in Type')},
            'number_of_days': {'input': 'number_of_days', 'label': _('Search in Days')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
        }

        timeoff_groups = request.env['hr.leave'].search([])

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]       

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('holiday_status_id', 'all'):
                search_domain = OR([search_domain, [('holiday_status_id', 'ilike', search)]])
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            domain += search_domain
        domain += [('employee_id.user_id', '=', http.request.env.context.get('uid'))] 
        timeoff_count = request.env['hr.leave'].search_count(domain)

        # pager
        pager = portal_pager(
            url="/my/timeoffs",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search},
            total=timeoff_count,
            page=page,
            step=self._items_per_page
        )

        _timeoff = request.env['hr.leave'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_timeoff_history'] = _timeoff.ids[:100]

        grouped_timeoffs = [_timeoff]
                
        paging(0,0,1)
        paging(grouped_timeoffs)
        company_info = request.env['res.users'].search([('id','=',http.request.env.context.get('uid'))])
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_timeoffs': grouped_timeoffs,
            'page_name': 'timeoffs',
            'default_url': '/my/timeoffs',
            'pager': pager,
            'company_info': company_info,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
        })
        return request.render("ws_portal_leave.portal_my_timeoffs", values)   

    
    
    @http.route(['/leave/balance', '/leave/balance/<int:page>'], type='http', auth="user", website=True)
    def portal_leave_balance(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'update': {'label': _('Last Update'), 'order': 'write_date desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'cancel','confirm','refuse','validate1','validate'])]},
            'draft': {'label': _('To Submit'), 'domain': [('state', '=', 'draft')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},  
            'confirm': {'label': _('To Approve'), 'domain': [('state', '=', 'confirm')]},
            'refuse': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]}, 
            'validate1': {'label': _('Second Approved'), 'domain': [('state', '=', 'validate1')]},
            'validate': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
        }
        searchbar_inputs = { 
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'holiday_status_id': {'input': 'holiday_status_id', 'label': _('Search in Type')},
            'number_of_days': {'input': 'number_of_days', 'label': _('Search in Days')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]       

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('holiday_status_id', 'all'):
                search_domain = OR([search_domain, [('holiday_status_id', 'ilike', search)]])
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            domain += search_domain
        domain += [('employee_id.user_id', '=', http.request.env.context.get('uid'))] 
        domain += [('fiscal_year', '=', fields.date.today().year )]
        allocation_count = request.env['hr.leave.allocation'].sudo().search_count(domain)

        # pager
        pager = portal_pager(
            url="/leave/balance",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search},
            total=allocation_count,
            page=page,
            step=self._items_per_page
        )

        _allocation = request.env['hr.leave.allocation'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_allocatiion_history'] = _allocation.ids[:100]
        grouped_allocations = [_allocation]        
        paging(0,0,1)
        paging(grouped_allocations)
        company_info = request.env['res.users'].search([('id','=',http.request.env.context.get('uid'))])
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_allocations': grouped_allocations,
            'page_name': 'balance',
            'default_url': '/leave/balance',
            'pager': pager,
            'company_info': company_info,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
        })
        return request.render("ws_portal_leave.portal_leave_balances", values)   

   
    @http.route(['/my/timeoff/<int:timeoff_id>'], type='http', auth="user", website=True)
    def portal_my_timeoff(self, timeoff_id, access_token=None, **kw):
        try:
            timeoff_sudo = self._document_check_access('hr.leave', timeoff_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        next_id = 0
        pre_id = 0
        timeoff_user_flag = 0

                
        timeoff_id_list = paging(0,1,0)
        next_next_id = 0
        timeoff_id_list.sort()
        length_list = len(timeoff_id_list)
        length_list = length_list - 1
        if length_list != 0:
            if timeoff_id in timeoff_id_list:
                timeoff_id_loc = timeoff_id_list.index(timeoff_id)
                if timeoff_id_loc == 0:
                    next_id = 1
                    pre_id = 0
                elif timeoff_id_loc == length_list:
                    next_id = 0
                    pre_id = 1
                else:
                    next_id = 1
                    pre_id = 1
        else:
            next_id = 0
            pre_id = 0
        values = self._timeoff_get_page_view_values(timeoff_sudo,next_id, pre_id,access_token, **kw) 
        return request.render("ws_portal_leave.portal_my_timeoff", values)

    @http.route(['/timeoff/next/<int:timeoff_id>'], type='http', auth="user", website=True)
    def portal_my_next_timeoff(self, timeoff_id, access_token=None, **kw):
        timeoff_id_list = paging(0,1,0)
        next_next_id = 0
        timeoff_id_list.sort()
        length_list = len(timeoff_id_list)
        if length_list == 0:
            return request.redirect('/my')
        length_list = length_list - 1
        if timeoff_id in timeoff_id_list:
            timeoff_id_loc = timeoff_id_list.index(timeoff_id)
            next_next_id = timeoff_id_list[timeoff_id_loc + 1] 
            next_next_id_loc = timeoff_id_list.index(next_next_id)
            if next_next_id_loc == length_list:
                next_id = 0
                pre_id = 1
            else:
                next_id = 1
                pre_id = 1      
        else:
            buffer_larger = 0
            buffer_smaller = 0
            buffer = 0
            for ids in timeoff_id_list:
                if ids < timeoff_id:
                    buffer_smaller = ids
                if ids > timeoff_id:
                    buffer_smaller = ids
                if buffer_larger and buffer_smaller:
                    break
            if buffer_larger:
                next_next_id = buffer_smaller
            elif buffer_smaller:
                next_next_id = buffer_larger
                
            next_next_id_loc = timeoff_id_list.index(next_next_id)
            length_list = len(timeoff_id_list)
            length_list = length_list + 1
            if next_next_id_loc == length_list:
                next_id = 0
                pre_id = 1
            elif next_next_id_loc == 0:
                next_id = 1
                pre_id = 0
            else:
                next_id = 1
                pre_id = 1
         
        values = []
        active_user = http.request.env.context.get('uid')
        id = timeoff_id
        try:
            timeoff_sudo = self._document_check_access('hr.leave', next_next_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        

        values = self._timeoff_get_page_view_values(timeoff_sudo,next_id, pre_id, access_token, **kw) 
        return request.render("ws_portal_leave.portal_my_timeoff", values)

  
    @http.route(['/timeoff/pre/<int:timeoff_id>'], type='http', auth="user", website=True)
    def portal_my_pre_timeoff(self, timeoff_id, access_token=None, **kw):
        
        timeoff_id_list = paging(0,1,0)
        pre_pre_id = 0
        timeoff_id_list.sort()
        length_list = len(timeoff_id_list)
    
        if length_list == 0:
            return request.redirect('/my')
        
        length_list = length_list - 1
        if timeoff_id in timeoff_id_list:
            timeoff_id_loc = timeoff_id_list.index(timeoff_id)
            pre_pre_id = timeoff_id_list[timeoff_id_loc - 1] 
            pre_pre_id_loc = timeoff_id_list.index(timeoff_id)

            if timeoff_id_loc == 1:
                next_id = 1
                pre_id = 0
            else:
                next_id = 1
                pre_id = 1      
        else:
            buffer_larger = 0
            buffer_smaller = 0
            buffer = 0
            for ids in timeoff_id_list:
                if ids < timeoff_id:
                    buffer_smaller = ids
                if ids > timeoff_id:
                    buffer_smaller = ids
                if buffer_larger and buffer_smaller:
                    break
            if buffer_smaller:
                pre_pre_id = buffer_smaller
            elif buffer_larger:
                pre_pre_id = buffer_larger
                
            pre_pre_id_loc = timeoff_id_list.index(pre_pre_id)
            length_list = len(timeoff_id_list)
            length_list = length_list -1
            if pre_pre_id_loc == 0:
                next_id = 1
                pre_id = 0
            elif pre_pre_id_loc == length_list:
                next_id = 0
                pre_id = 1
            else:
                next_id = 1
                pre_id = 1
   
        values = []

        id = pre_pre_id
        try:
            timeoff_sudo = self._document_check_access('hr.leave', pre_pre_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        timeoff_user_flag = 0
        values = self._timeoff_get_page_view_values(timeoff_sudo, next_id,pre_id, access_token, **kw) 
        return request.render("ws_portal_leave.portal_my_timeoff", values)
