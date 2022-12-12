# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import requests
import base64
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    zacuta_id = fields.Many2one('zacuta.order', string='Zacuta ID')

    
 