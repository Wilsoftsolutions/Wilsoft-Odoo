# -*- coding: utf-8 -*-
{
    'name': "Portal Service Actions",

    'summary': """
    Actions for Portal Service
        """,

    'description': """
        Server Actions
    """,

    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '14.0.0.4',

    # any module necessary for this one to work correctly
    'depends': ['de_portal_hr_service'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_service_actions_views.xml',
        'views/portal_actions_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
