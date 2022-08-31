# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    
    def action_get_portal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "View Portal",
            'target': 'new',
            'url': '/my/home'
        }
     

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    
    employee_type_id = fields.Many2one('emp.type.category',  string='Employee Category', domain="[('company_id','=',company_id)]"  )
    
    
class HrEmployee(models.Model):
    _name = 'emp.type.category'
    _description = 'Employee Type'
    
    
    name = fields.Char(string='Description')
    company_id = fields.Many2one('res.company',  string='Company', default=lambda self: self.env.company )    
    employee_id = fields.Many2one('hr.employee',  string='Employee')    
    
    