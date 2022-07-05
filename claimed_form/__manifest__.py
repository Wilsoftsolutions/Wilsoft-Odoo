# -*- coding: utf-8 -*-
{
    'name': "Claimed Form",

    'summary': """This module is design for Claimed form""",

    'description': """This module is design for Claimed form    """,

    'author': "Muhammad Ismail",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/claimed_form_view.xml',
        'views/qc_remark.xml',
        'views/claim_remark.xml',
     
        'data/claim_sequence.xml',

    ],

}
