# -*- coding: utf-8 -*-

from . import config
from . import update
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.osv import expression
from odoo.exceptions import UserError
from collections import OrderedDict
from datetime import date, datetime, timedelta
from operator import itemgetter
from datetime import datetime , date
from odoo import exceptions
from dateutil.relativedelta import relativedelta
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR

def attendance_page_content(flag = 0):
    emps = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
    managers = emps.parent_id.name
    employee_name = emps
    return {
        'emps': emps,
        'managers': managers,
        'employee_name': employee_name,
        'success_flag' : flag,
    }


def print_page_content(flag = 0):
    emps = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
    managers = emps.parent_id.name
    employee_name = emps
    return {
        'emps': emps,
        'managers': managers,
        'employee_name': employee_name,
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
                
                
def kattendance_page_content(flag = 0):
    employees = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
    company_info = request.env['res.users'].sudo().search([('id','=',http.request.env.context.get('uid'))])
    return {
        'employees' : employees,
        'success_flag' : flag,
        'company_info' : company_info
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
                
                
        
class CreateAttendance(http.Controller):
    
    
    @http.route('/kattendance/create/checkin',type="http", website=True, auth='user')
    def kattendance_create_checkin(self, **kw):
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        employee_id = kattendance_page_content()['employees']
        
        att_exists = request.env['hr.attendance'].sudo().search([('employee_id','=', employee_id.id),('check_out','=',False),('att_date','=', fields.date.today()),('remarks','=','WFH(Work From Home)')], order='check_in desc', limit=1)
        if att_exists:
            print(att_exists.check_in)
            return request.render("ws_hr_attendance.already_checkin_exists",kattendance_page_content()) 
        
        else:    
            att_val = {
                'employee_id': employee_id.id,
                'att_date': fields.date.today(),
                'remarks': 'WFH(Work From Home)',
                'check_in': current_datetime,
            }
            record = request.env['hr.attendance'].sudo().create(att_val)
            return request.render("ws_hr_attendance.kattendance_checkin_template",kattendance_page_content()) 
    
    
    @http.route('/kattendance/create/checkout',type="http", website=True, auth='user')
    def kattendance_create_checkout(self, **kw):
        print('datetime.now()',datetime.now())
        print('datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")',datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        employee_id = kattendance_page_content()['employees']
        att_date =  fields.date.today()
        att_exists = request.env['hr.attendance'].sudo().search([('employee_id','=', employee_id.id),('check_out','=',False),('att_date','=',att_date),('remarks','=','WFH(Work From Home)')], order="check_in asc" , limit=1)
        
        if att_exists:
            att_val = {
                'check_out':current_datetime,
                'remarks': 'WFH(Work From Home)', 
            }
            record = att_exists.sudo().write(att_val)
            return request.render("ws_hr_attendance.kattendance_checkin_template",kattendance_page_content()) 
        else:
            return request.render("ws_hr_attendance.no_checkin_exists",kattendance_page_content()) 

    
    
 
    
    
    @http.route('/hr/attendance/rectify/',type="http", website=True, auth='user')
    def approvals_create_template(self, **kw):
        return request.render("ws_hr_attendance.attendance_create_rectify", attendance_page_content())


    @http.route('/hr/attendance/print/',type="http", website=True, auth='user')
    def action_print_attendance(self, **kw):
        return request.render("ws_hr_attendance.print_attendance_report", print_page_content())
    
   
    
    
    
    @http.route('/hr/attendance/rectify/save', type="http", auth="public", website=True)
    def create_rectify_attendance(self, **kw):
        checkin_date_in = kw.get('check_in')
        
        if kw.get('date'):
            if kw.get('date') > str(date.today()):
                return request.render("ws_hr_attendance.cannot_submit_future_days_commitment_msg", attendance_page_content())
            
        if kw.get('id'):
            exist_attendance1 = request.env['hr.attendance'].sudo().search([('id','=',int(kw.get('id')))])
            if not kw.get('check_out'):
                check_out =  exist_attendance1.check_out
                checkin1_date_rectify = check_out.strftime('%Y-%m-%d')
                checkin_date_rectify = datetime.strptime(str(checkin1_date_rectify) , '%Y-%m-%d')
                checkin_duration_obj = datetime.strptime(kw.get('check_in'), '%H:%M')
                checkin_date_in = checkin_date_rectify + timedelta(hours=checkin_duration_obj.hour, minutes=checkin_duration_obj.minute)
                if kw.get('night_shift'):
                    check_out1 = checkin1_date_rectify
                    if checkin1_date_rectify:
                        check_out1 = datetime.strptime(checkin1_date_rectify, '%Y-%m-%d') - timedelta(1)
                    checkin_date_rectify = check_out1
                    checkin_duration_obj = datetime.strptime(kw.get('check_in'), '%H:%M')
                    checkin_date_in = checkin_date_rectify + timedelta(hours=checkin_duration_obj.hour, minutes=checkin_duration_obj.minute)    
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  checkin_date_in - relativedelta(hours =+ 5),
                    'check_out': check_out,
                    'partial': 'Check In Time Missing',
                    'date':  check_out,
                    'attendance_id':  int(kw.get('id')),
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)
                if kw.get('partial'):
                    record.update({
                        'partial': 'Partial',
                    })
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})
            elif not kw.get('check_in'):
                
                check_in =  exist_attendance1.check_in
                checkout1_date_rectify = check_in.strftime('%Y-%m-%d')
                checkout_date_rectify = datetime.strptime(str(checkout1_date_rectify) , '%Y-%m-%d')
                checkout_duration_obj = datetime.strptime(kw.get('check_out'), '%H:%M')
                checkout_date_in = checkout_date_rectify + timedelta(hours=checkout_duration_obj.hour, minutes=checkout_duration_obj.minute)
                if kw.get('night_shift'):
                    check1_in = checkout1_date_rectify
                    if checkout1_date_rectify:
                        check1_in = datetime.strptime(checkout1_date_rectify, '%Y-%m-%d') + timedelta(1) 
                    checkout_date_rectify = datetime.strptime(str(check1_in) , '%Y-%m-%d %H:%M:%S')
                    checkout_duration_obj = datetime.strptime(kw.get('check_out'), '%H:%M')
                    checkout_date_in = checkout_date_rectify + timedelta(hours=checkout_duration_obj.hour, minutes=checkout_duration_obj.minute)
                
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  check_in,
                    'check_out': checkout_date_in - relativedelta(hours =+ 5),
                    'date':  check_in,
                    'partial': 'Out Time Missing', 
                    'attendance_id':  int(kw.get('id')),
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)
                if kw.get('partial'):
                    record.update({
                        'partial': 'Partial',
                    })
                    
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})
                
        else:
            if kw.get('partial'):
                if  not kw.get('check_in_time'):
                    raise UserError('Please slect Time In') 
                if  not kw.get('check_out_time'):
                    raise UserError('Please slect Time Out') 
                timein_data = kw.get('check_in_time').split(":")
                check_in_hour = 0
                check_in_minute = 0
                time_count = 0
                for deltatime in timein_data:
                    if time_count == 0:
                        check_in_hour =  deltatime
                    time_count += 1
                    if time_count:
                        check_in_minute =  deltatime  
                timeout_data = kw.get('check_out_time').split(":")
                check_out_hour = 0
                check_out_minute = 0
                time_count = 0
                for deltatime in timeout_data:
                    if time_count == 0:
                        check_out_hour =  deltatime
                    time_count += 1
                    if time_count:
                        check_out_minute =  deltatime          
                timeout_data = float(kw.get('check_in_time').replace(":", "."))
                check_in_datetime = datetime.strptime(kw.get('date_partial'), '%Y-%m-%d') + relativedelta(hours =+ int(check_in_hour), minutes = int(check_in_minute))
                check_out_datetime = datetime.strptime(kw.get('date_partial'),'%Y-%m-%d') + relativedelta(hours =+ int(check_out_hour), minutes = int(check_out_minute))
                
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  check_in_datetime - relativedelta(hours =+ 5),
                    'check_out': check_out_datetime - relativedelta(hours =+ 5),
                    'partial': 'Partial',
                    'date':  check_in_datetime,
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})
        
            else:
                employee_data = request.env['hr.employee'].sudo().search([('id','=',int(kw.get('employee_id')))], limit=1)
                shift = employee_data.resource_calendar_id
                if not shift:    
                    shift = request.env['resource.calendar'].sudo().search([('company_id','=',employee_data.company_id.id)], limit=1)
                hours_from = 8
                hours_to =  16
                
                for shift_line in shift.attendance_ids:
                    hours_from =   shift_line.hour_from     
                    hours_to = shift_line.hour_to 
                attendance_data_in = datetime.strptime(kw.get('check_in'), '%Y-%m-%d') + relativedelta(hours =+ hours_from)
                att_date_out = datetime.strptime(kw.get('check_out'), '%Y-%m-%d') + relativedelta(hours =+ hours_to)
                attendance_data_out =  datetime.strptime(kw.get('check_out'), '%Y-%m-%d') + relativedelta(hours =+ hours_to)
                
                restrict_date = fields.date.today() + timedelta(30)     
                if kw.get('check_in') > str(restrict_date):
                    return request.render("ws_hr_attendance.cannot_submit_future_days_commitment_msg", attendance_page_content())
                if kw.get('check_out') > str(restrict_date):
                    return request.render("ws_hr_attendance.cannot_submit_future_days_commitment_msg", attendance_page_content())
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  attendance_data_in - relativedelta(hours =+ 5),
                    'check_out': attendance_data_out - relativedelta(hours =+ 5),
                    'partial': 'Full',
                    'date':  kw.get('check_in'),
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)

                if kw.get('partial'):
                    record.update({
                            'partial': 'Partial',
                    })
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})

    
    @http.route('/attendance/rectify/reverse/save', type="http", auth="public", website=True)
    def reverse_rectify_attendance(self, **kw):
        checkin_date_in = kw.get('check_in')
        
        if kw.get('date'):
            if kw.get('date') > str(date.today()):
                return request.render("ws_hr_attendance.cannot_submit_future_days_commitment_msg", attendance_page_content())
            
        if kw.get('id'):
            exist_attendance1 = request.env['hr.attendance'].search([('id','=',int(kw.get('id')))])
            if kw.get('check_out'):
                check_out =  exist_attendance1.check_out
                checkin1_date_rectify = check_out.strftime('%Y-%m-%d')
                checkin_date_rectify = datetime.strptime(str(checkin1_date_rectify) , '%Y-%m-%d')
                checkin_duration_obj = datetime.strptime(kw.get('check_out'), '%H:%M')
                checkin_date_in = checkin_date_rectify + timedelta(hours=checkin_duration_obj.hour, minutes=checkin_duration_obj.minute)
                if kw.get('night_shift'):
                    check_reverse_out1 = checkin1_date_rectify
                    if checkin1_date_rectify:
                        check_reverse_out1 = datetime.strptime(checkin1_date_rectify, '%Y-%m-%d') + timedelta(1)
                    checkin_date_rectify = check_reverse_out1
                    checkin_date_in = checkin_date_rectify + timedelta(hours=checkin_duration_obj.hour, minutes=checkin_duration_obj.minute)
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  check_out,
                    'check_out': checkin_date_in - relativedelta(hours =+ 5),
                    'partial': 'Out Time Missing',
                    'date':  check_out,
                    'attendance_id':  int(kw.get('id')),
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)
                if kw.get('partial'):
                    record.update({
                        'partial': 'Partial',
                    })
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})
            elif kw.get('check_in'):
                
                check_in =  exist_attendance1.check_in
                checkout1_date_rectify = check_in.strftime('%Y-%m-%d')
                checkout_date_rectify = datetime.strptime(str(checkout1_date_rectify) , '%Y-%m-%d')
                checkout_duration_obj = datetime.strptime(kw.get('check_in'), '%H:%M')
                checkout_date_in = checkout_date_rectify + timedelta(hours=checkout_duration_obj.hour, minutes=checkout_duration_obj.minute)
                if kw.get('night_shift'):
                    check1_in =  datetime.strptime(str(checkout1_date_rectify) , '%Y-%m-%d') - timedelta(1) 
                    checkout_date_rectify = check1_in
                    checkout_duration_obj = datetime.strptime(kw.get('check_in'), '%H:%M')
                    checkout_date_in = checkout_date_rectify + timedelta(hours=checkout_duration_obj.hour, minutes=checkout_duration_obj.minute)
                
                rectify_val = {
                    'reason': kw.get('description'),
                    'employee_id': int(kw.get('employee_id')),
                    'check_in':  checkout_date_in - relativedelta(hours =+ 5),
                    'check_out': check_in,
                    'date':  check_in,
                    'partial': 'Check In Time Missing', 
                    'attendance_id':  int(kw.get('id')),
                }
                record = request.env['hr.attendance.rectify'].sudo().create(rectify_val)
                if kw.get('partial'):
                    record.update({
                        'partial': 'Partial',
                    })
                    
               
       
                record.action_submit()
                return request.render("ws_hr_attendance.rectification_submited", {})        

    
    
       
   


class CustomerPortal(CustomerPortal):
    
    
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'kattendance_count' in counters:
            values['kattendance_count'] = request.env['hr.attendance'].sudo().search_count([('employee_id.user_id', '=', http.request.env.context.get('uid') )])
        return values
  
    def _resignation_get_page_view_values(self,kattendance, next_id = 0,pre_id= 0, kattendance_user_flag = 0, access_token = None, **kwargs):
        company_info = request.env['res.users'].sudo().search([('id','=',http.request.env.context.get('uid'))])
        values = {
            'page_name': 'kisok attendance',
            'kattendance': kattendance,
            'kattendance_user_flag':kattendance_user_flag,
            'next_id' : next_id,
            'company_info': company_info,
            'pre_id' : pre_id,
        }
        return self._get_page_view_values(kattendance, access_token, values, 'my_timeoff_history', False, **kwargs)
    

    @http.route(['/my/kattendance', '/my/kattendance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_kattendances(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        print('----------------in py method')
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'employee_id': {'label': _('Employee'), 'order': 'employee_id desc' },
            'update': {'label': _('Last Update'), 'order': 'write_date desc'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            
        }
                                 
        
        searchbar_inputs = {  
            'name': {'input': 'name', 'label': _('Search in Employee')},
            'id': {'input': 'id', 'label': _('Search in Ref#')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
        }

#         timeoff_groups = request.env['hr.resignation'].search([])

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
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            domain += search_domain
        domain += [('remarks','=','WFH(Work From Home)')]    
        kattendance_count = request.env['hr.attendance'].sudo().search_count(domain)

        # pager
        pager = portal_pager(
            url="/my/kattendance",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'seissuesarch_in': search_in, 'search': search},
            total=555,
            page=page,
            step=self._items_per_page
        )

        _kattendance = request.env['hr.attendance'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_timeoff_history'] = _kattendance.ids[:100]

        grouped_kattendances = [_kattendance]
        grouped_check_in = True
        grouped_check_out = False
                
        paging(0,0,1)
        paging(grouped_kattendances)
        company_info = request.env['res.users'].sudo().search([('id','=',http.request.env.context.get('uid'))])
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_kattendances': grouped_kattendances,
            'grouped_check_in': grouped_check_in,
            'grouped_check_out': grouped_check_out,
            'page_name': 'Kiosk Attendance',
            'default_url': '/my/kattendance',
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
        return request.render("ws_hr_attendance.portal_my_kattendances", values)   

    
    
    def _show_report_portal(self, model, report_type, employee, start_date, end_date, report_ref, download=False):
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


    
    @http.route('/hr/attendance/print/report',type="http", website=True,download=False, auth='user')
    def action_print_attendance_report(self, **kw):
        report_type='pdf'
        order_sudo = 'hr.attendance'
        download = False
        employee = request.env['hr.employee'].sudo().search([('id','=',int(kw.get('employee_id')))]).id
        start_date = kw.get('check_in')
        end_date = kw.get('check_out')
        return self._show_report_portal(model=order_sudo, report_type=report_type,employee=employee, start_date=start_date, end_date=end_date, report_ref='ws_hr_attendance.open_hr_report_wizard_action', download=download)
    
    
    @http.route(['/hr/attendance/cancel/<int:attendance_id>'], type='http', auth="public", website=True)
    def action_cancel(self,attendance_id , access_token=None, **kw):
        id=attendance_id
        rectification = request.env['hr.attendance.rectify'].sudo().browse(id)
        approval_rectification = request.env['hr.approval.request'].sudo().search([('record_id','=',id)])
        
        approval_rectification.action_refuse()
        rectification.action_refuse()
        try:
            rectification_sudo = self._document_check_access('hr.attendance.rectify', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._attendance_get_page_view_values(rectification_sudo, **kw) 
        return request.render("ws_hr_attendance.rectification_cancel", {})
    
    
    @http.route(['/hr/attendance/rectify/<int:attendance_id>'], type='http', auth="public", website=True)
    def attendance_edit_template(self,attendance_id, access_token=None ,**kw):
        id = attendance_id
        try:
            expense_sudo = self._document_check_access('hr.attendance', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._attendance_get_page_view_values(expense_sudo, **kw) 
        exist_attendance = request.env['hr.attendance'].sudo().browse(id)
        employees = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
        managers = employees.parent_id.name
        employee_name = employees
        checkin_date_in = str(exist_attendance.check_in)
        date_processing_in = checkin_date_in.replace(':', '-').replace('T', '-').split('-')
        checkout_date_in = str(exist_attendance.check_out) 
        date_processing_out = checkout_date_in.replace(':', '-').replace('T', '-').split('-')
        values.update({
            'exist_attendance': exist_attendance,
            'date_processing_in': date_processing_in,
            'managers': managers,
            'employee_name': employee_name,
            'date_processing_out': date_processing_out,
             'emps' : employees,
        })
        return request.render("ws_hr_attendance.attendance_rectify", values)


    @http.route(['/hr/attendance/rectify/reverse/<int:attendance_id>'], type='http', auth="public", website=True)
    def attendance_edit_reverse_template(self,attendance_id, access_token=None ,**kw):
        id = attendance_id
        try:
            expense_sudo = self._document_check_access('hr.attendance', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._attendance_get_page_view_values(expense_sudo, **kw) 
        exist_attendance = request.env['hr.attendance'].sudo().browse(id)
        employees = request.env['hr.employee'].sudo().search([('user_id','=',http.request.env.context.get('uid'))])
        managers = employees.parent_id.name
        employee_name = employees
        checkin_date_in = str(exist_attendance.check_in)
        date_processing_in = checkin_date_in.replace(':', '-').replace('T', '-').split('-')
        checkout_date_in = str(exist_attendance.check_out) 
        date_processing_out = checkout_date_in.replace(':', '-').replace('T', '-').split('-')
        values.update({
            'exist_attendance': exist_attendance,
            'date_processing_in': date_processing_in,
            'managers': managers,
            'employee_name': employee_name,
            'date_processing_out': date_processing_out,
             'emps' : employees,
        })
        return request.render("ws_hr_attendance.attendance_rectify_reverse", values)
    
    

  
    def _rectify_attendance_get_page_view_values(self,rectify, next_id = 0,pre_id= 0, attendance_user_flag = 0, access_token = None, **kwargs):
        values = {
            'page_name' : 'rectify',
            'rectify' : rectify,
            'attendance_user_flag': attendance_user_flag,
            'next_id' : next_id,
            'pre_id' : pre_id,
        }
        return self._get_page_view_values(attendance, access_token, values, 'my_attendance_history', False, **kwargs)

    
    @http.route(['/hr/rectify/attendances', '/hr/rectify/attendances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_hr_rectify_attendances(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None,
                         search_in='content', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'id': {'label': _('Default'), 'order': 'id asc'},
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'employee_id desc' },
            'update': {'label': _('Last Update'), 'order': 'write_date desc'},
        }
                                                
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
           
        searchbar_inputs = {
            'id': {'input': 'id', 'label': _('Search in No#')},
            'employee_id.name': {'input': 'employee_id.name', 'label': _('Search in Employee')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
        }
        date = fields.date.today() - timedelta(30)
        project_groups = request.env['hr.attendance.rectify'].search([('employee_id.user_id','=', http.request.env.context.get('uid'))])

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']
#         domain = []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]       

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'ID'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('employee_id.name', 'Employee'):
                search_domain = OR([search_domain, [('employee_id.name', 'ilike', search)]])
            domain += search_domain
        domain += [('employee_id.user_id', '=', http.request.env.context.get('uid'))] 
        rectify_count = request.env['hr.attendance.rectify'].search_count(domain)

        pager = portal_pager(
            url="/hr/rectify/attendances",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search},
            total=rectify_count,
            page=page,
            step=self._items_per_page
        )

        _rectification = request.env['hr.attendance.rectify'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_rectify_attendance_history'] = _rectification.ids[:100]

        grouped_rectify_attendances = [project_groups]
                
        paging(0,0,1)
        paging(grouped_rectify_attendances)
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_rectify_attendances': grouped_rectify_attendances,
            'page_name': 'rectify',
            'default_url': '/hr/rectify/attendances',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
        })
        return request.render("ws_hr_attendance.portal_hr_rectify_attendances", values)
    
    
    

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'attendance_count' in counters:
            values['attendance_count'] = request.env['hr.attendance'].search_count([])
        return values
  
    def _attendance_get_page_view_values(self,attendance, next_id = 0,pre_id= 0, attendance_user_flag = 0, access_token = None, **kwargs):
        values = {
            'page_name' : 'Attendance',
            'attendance' : attendance,
            'attendance_user_flag': attendance_user_flag,
            'next_id' : next_id,
            'pre_id' : pre_id,
        }
        return self._get_page_view_values(attendance, access_token, values, 'my_attendance_history', False, **kwargs)

    @http.route(['/hr/attendances', '/hr/attendances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_hr_attendances(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None,
                         search_in='content', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'id': {'label': _('Default'), 'order': 'id asc'},
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'employee_id desc' },
            'update': {'label': _('Last Update'), 'order': 'write_date desc'},
        }
                                                
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
           
        searchbar_inputs = {
            'id': {'input': 'id', 'label': _('Search in No#')},
            'employee_id.name': {'input': 'employee_id.name', 'label': _('Search in Employee')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
        }
        date = fields.date.today() - timedelta(70)
        project_groups = request.env['hr.attendance'].search([('att_date','>=', date)])

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']
#         domain = []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]       

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'ID'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('employee_id.name', 'Employee'):
                search_domain = OR([search_domain, [('employee_id.name', 'ilike', search)]])
            domain += search_domain
        domain += [('employee_id.user_id', '=', http.request.env.context.get('uid'))] 
        attendance_count = request.env['hr.attendance'].sudo().search_count(domain)

        pager = portal_pager(
            url="/hr/attendances",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search},
            total=attendance_count,
            page=page,
            step=self._items_per_page
        )

        _attendances = request.env['hr.attendance'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_attendance_history'] = _attendances.ids[:100]

        grouped_attendances = [project_groups]
                
        paging(0,0,1)
        paging(grouped_attendances)
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_attendances': grouped_attendances,
            'page_name': 'attendance',
            'default_url': '/hr/attendances',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
        })
        return request.render("ws_hr_attendance.portal_hr_attendances", values)   

   
    @http.route(['/hr/attendance/<int:attendance_id>'], type='http', auth="user", website=True)
    def portal_hr_attendance(self, attendance_id, access_token=None, **kw):
        values = []

        id = attendance_id
        try:
            attendance_sudo = self._document_check_access('hr.attendance', attendance_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        next_id = 0
        pre_id = 0
        attendance_user_flag = 0

                
        attendance_id_list = paging(0,1,0)
        next_next_id = 0
        attendance_id_list.sort()
        length_list = len(attendance_id_list)
        length_list = length_list - 1
        if length_list != 0:
            if attendance_id in attendance_id_list:
                attendance_id_loc = attendance_id_list.index(attendance_id)
                if attendance_id_loc == 0:
                    next_id = 1
                    pre_id = 0
                elif attendance_id_loc == length_list:
                    next_id = 0
                    pre_id = 1
                else:
                    next_id = 1
                    pre_id = 1
        else:
            next_id = 0
            pre_id = 0

        values = self._attendance_get_page_view_values(attendance_sudo,next_id, pre_id, attendance_user_flag,access_token, **kw) 
        return request.render("ws_hr_attendance.portal_hr_attendance", values)

    @http.route(['/attendance/next/<int:attendance_id>'], type='http', auth="user", website=True)
    def portal_my_next_attendance(self, attendance_id, access_token=None, **kw):
        
        attendance_id_list = paging(0,1,0)
        next_next_id = 0
        attendance_id_list.sort()
        
        length_list = len(attendance_id_list)
        if length_list == 0:
            return request.redirect('/hr')
        length_list = length_list - 1
        
        if attendance_id in attendance_id_list:
            attendance_id_loc = attendance_id_list.index(attendance_id)
            next_next_id = attendance_id_list[attendance_id_loc + 1] 
            next_next_id_loc = attendance_id_list.index(next_next_id)
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
            for ids in attendance_id_list:
                if ids < attendance_id:
                    buffer_smaller = ids
                if ids > attendance_id:
                    buffer_smaller = ids
                if buffer_larger and buffer_smaller:
                    break
            if buffer_larger:
                next_next_id = buffer_smaller
            elif buffer_smaller:
                next_next_id = buffer_larger
                
            next_next_id_loc = attendance_id_list.index(next_next_id)
            length_list = len(attendance_id_list)
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

        id = attendance_id
        try:
            attendance_sudo = self._document_check_access('hr.attendance', next_next_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        

        attendance_user_flag = 0


        values = self._attendance_get_page_view_values(attendance_sudo,next_id, pre_id, access_token, **kw) 
        return request.render("ws_hr_attendance.portal_hr_attendance", values)

  
    @http.route(['/attendance/pre/<int:attendance_id>'], type='http', auth="user", website=True)
    def portal_my_pre_attendance(self, attendance_id, access_token=None, **kw):
        
        attendance_id_list = paging(0,1,0)
        pre_pre_id = 0
        attendance_id_list.sort()
        length_list = len(attendance_id_list)
    
        if length_list == 0:
            return request.redirect('/my')
        
        length_list = length_list - 1
        if attendance_id in attendance_id_list:
            attendance_id_loc = attendance_id_list.index(attendance_id)
            pre_pre_id = attendance_id_list[attendance_id_loc - 1] 
            pre_pre_id_loc = attendance_id_list.index(attendance_id)

            if attendance_id_loc == 1:
                next_id = 1
                pre_id = 0
            else:
                next_id = 1
                pre_id = 1      
        else:
            buffer_larger = 0
            buffer_smaller = 0
            buffer = 0
            for ids in attendance_id_list:
                if ids < attendance_id:
                    buffer_smaller = ids
                if ids > attendance_id:
                    buffer_smaller = ids
                if buffer_larger and buffer_smaller:
                    break
            if buffer_smaller:
                pre_pre_id = buffer_smaller
            elif buffer_larger:
                pre_pre_id = buffer_larger
                
            pre_pre_id_loc = attendance_id_list.index(pre_pre_id)
            length_list = len(attendance_id_list)
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
            attendance_sudo = self._document_check_access('hr.attendance', pre_pre_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        

        attendance_user_flag = 0


        values = self._attendance_get_page_view_values(attendance_sudo, next_id,pre_id, access_token, **kw) 
        return request.render("ws_hr_attendance.portal_hr_attendance", values)

    
