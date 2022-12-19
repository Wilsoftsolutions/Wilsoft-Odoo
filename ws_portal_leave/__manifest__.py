# -*- coding: utf-8 -*-
{
    'name': "Portal Leave",

    'summary': """
        Leave Request From Portal
        """,

    'description': """
        Leave Request From Portal
    """,

    'author': "wilshiresolutions",
    'website': "http://www.wilshiresolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Leaves',
    'version': '15.0.0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 
                'hr_holidays',
                'portal',
                'rating',
                'de_portal_hr_service_actions',
                'de_hr_payroll_policy',
                'resource',
                'digest',
                'base',
                'hr',
               ],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_leave_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
