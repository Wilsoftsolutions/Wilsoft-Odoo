# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

class AccountFiscalyear(models.Model):
    _name = "account.fiscalyear.periods"
    _inherit = ['mail.thread']
    _description = "Fiscal Year"
    _rec_name = 'fiscal_year_id'

    fiscal_year_id = fields.Many2one('account.fiscal.year',required=True, tracking=True)
    code = fields.Char('Code',required=True, tracking=True,default='/',readonly=True)
    company_id = fields.Many2one('res.company', required=True,default=lambda self: self.env.company, tracking=True)
    date_start = fields.Date('Start Date',related='fiscal_year_id.date_from',store=True, tracking=True)
    date_stop = fields.Date('Ending Date',related='fiscal_year_id.date_to',store=True, tracking=True)
    period_ids = fields.One2many('account.month.period', 'fiscalyear_id', 'Periods', tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),('done', 'Closed')],
        'Status', readonly=True, default='draft', tracking=True)
    comments = fields.Text('Comments')

    @api.onchange('fiscal_year_id')
    def _onchange_fiscal_year_id(self):
        if self.fiscal_year_id:
            self.code = 'FY/'+str(self.fiscal_year_id.name)


    @api.model
    def create(self, vals):
        return super(AccountFiscalyear, self).create(vals)

    def open(self):
        for rec in self:
            rec.write({'state':'open'})


    def set_to_draft(self):
        for rec in self:
            rec.write({'state':'draft'})
    def done(self):
        for rec in self:
            rec.period_ids.write({'special':False})
            rec.write({'state':'done'})        

    #def get_month(self, date_from):
    #    locale = self.env.context.get('lang') or 'en_US'
    #    new_dates =  tools.ustr(babel.dates.format_date(date=date_from, format='MMMM y', locale=locale)) 
    #    return new_date        

    '''@api.multi
    @api.constrains('date_start','date_stop')
    def _check_period(self):
        for rec in self:
            if rec.date_start and rec.date_stop:
                if rec.date_start > rec.date_stop:
                    raise ValidationError(_('The start date must be before end date.'))
                fiscal_rec_start = self.search([('date_start','<=',rec.date_start),('date_stop','>=',rec.date_start),('id','!=',rec.id)])
                if fiscal_rec_start:
                    raise ValidationError(_('The start date is within other fiscal year period.'))
                fiscal_rec_end = self.search([('date_start','<=',rec.date_stop),('date_stop','>=',rec.date_stop),('id','!=',rec.id)])
                if fiscal_rec_end:
                    raise ValidationError(_('The end date is within other fiscal year period.'))'''
    _sql_constraints = [
        ('fiscalyear_per_company_uniq', 'unique(fiscal_year_id,company_id)', _('The Fiscal Year must be unique For Periods!'))
    ]            

    @api.constrains('date_start', 'date_stop', 'company_id')
    def _check_dates(self):
        for fy in self:
            # Starting date must be prior to the ending date
            date_from = fy.date_start
            date_to = fy.date_stop
            if date_to < date_from:
                raise ValidationError(_('The ending date must not be prior to the starting date.'))


            domain = [
                ('id', '!=', fy.id),
                ('company_id', '=', fy.company_id.id),
                '|', '|',
                '&', ('date_start', '<=', fy.date_start), ('date_stop', '>=', fy.date_start),
                '&', ('date_start', '<=', fy.date_stop), ('date_stop', '>=', fy.date_stop),
                '&', ('date_start', '<=', fy.date_start), ('date_stop', '>=', fy.date_stop),
            ]

            if self.search_count(domain) > 0:
                raise ValidationError(_('You can not have an overlap between two fiscal years, please correct the start and/or end dates of your fiscal years.'))



    def create_periods(self):
        period_obj = self.env['account.month.period']
        for rec in self:
            rec.period_ids.unlink()
            start_date = fields.Date.from_string(rec.date_start)
            end_date = fields.Date.from_string(rec.date_stop)
            index = 1
            while start_date < end_date:
                de = start_date + relativedelta(months=1, days=-1)

                if de > end_date:
                    de = end_date

                period_obj.create({
                    'sequence': index,
                    'code': '%02d/' % int(index) + start_date.strftime('%Y'),
                    'date_start': start_date.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': rec.id,
                })
                start_date = start_date + relativedelta(months=1)
                index += 1

class AccountMonthPeriod(models.Model):
    _name = "account.month.period"
    _description = "Account Month period"
    _inherit = ['mail.thread']
    _order = "date_start asc"

    sequence = fields.Integer('Sequence', default=1)
    code = fields.Char('Code', tracking=True)
    special = fields.Boolean('Opening/Closing', tracking=True)
    date_start = fields.Date('From', required=True, tracking=True)
    date_stop = fields.Date('To', required=True, tracking=True)
    fiscalyear_id = fields.Many2one('account.fiscalyear.periods', 'Fiscal Year', tracking=True)
    company_id = fields.Many2one('res.company',string='Company',related='fiscalyear_id.company_id',store=True)

    def get_closest_open_date(self,dates):
        period = self.sudo().with_context(company_id=self.env.company.id).search([('date_start', '<=', dates), ('date_stop', '>=', dates),('special','=',True),('company_id','=',self.env.company.id)],limit=1)
        if period:
            return dates
        else:
            period = self.sudo().with_context(company_id=self.env.company.id).search([('date_start', '>=', dates),('special','=',True),('company_id','=',self.env.company.id)],limit=1)
            if period:
                return period.date_start
            else:
                return dates


    def get_closest_open_by_period(self,dates):
        period = self.sudo().with_context(company_id=self.env.company.id).search([('date_start', '<=', dates), ('date_stop', '>=', dates),('special','=',True),('company_id','=',self.env.company.id)],limit=1)
        if period:
            return {'date_from':period['date_start'],'date_to':period['date_stop']}
        else:
            period = self.sudo().with_context(company_id=self.env.company.id).search([('special','=',True),('company_id','=',self.env.company.id)],order='date_start desc',limit=1)
            if period:
                return {'date_from':period['date_start'],'date_to':period['date_stop']}    
            else:          
                return False          
                 
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_fiscalyear_lock_date(self):
        res = super(AccountMove, self)._check_fiscalyear_lock_date()
        if res:
            for rec in self:
                fiscal_year_obj = self.env['account.fiscalyear.periods']
                period_obj = self.env['account.month.period']
                fiscal_rec = fiscal_year_obj.sudo().with_context(company_id=rec.company_id.id).search([('date_start','<=',rec.date),('date_stop','>=',rec.date),('company_id','=',rec.company_id.id)],limit=1)
                if not fiscal_rec:
                    raise ValidationError(_('The Date Must Be Within Defined Fiscal Year Period'))
                elif fiscal_rec.state == 'open':
                    period_rec = period_obj.sudo().with_context(company_id=rec.company_id.id).search([('date_start', '<=', rec.date), ('date_stop', '>=', rec.date),('fiscalyear_id','=',fiscal_rec.id)],limit=1)
                    if not period_rec:
                        raise ValidationError(
                            _('The date must be within the period duration.'))
                    elif not period_rec.special:
                        raise ValidationError(_('The Fiscal year period is closed'))
                    else:return True
                else:raise ValidationError(
                            _('The Fiscal year must opened first'))
        else: return res                         
