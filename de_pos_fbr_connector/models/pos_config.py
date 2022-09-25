# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import requests
import json
import datetime
import traceback
from datetime import datetime

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_fbr = fields.Boolean("Enable FBR")
    fbr_url = fields.Char("API URL")
    fbr_authorization = fields.Char("Token")
    pos_id = fields.Char("POS ID")
