# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import requests
import json
import datetime
import traceback
from datetime import datetime


class Product(models.Model):
    _inherit = 'product.template'

    pct_code = fields.Char("PCT Code", required=False)