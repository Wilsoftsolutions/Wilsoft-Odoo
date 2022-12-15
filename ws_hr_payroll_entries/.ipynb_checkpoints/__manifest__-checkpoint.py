# -*- coding: utf-8 -*-
{
    'name': "Payroll Work Entries",

    'summary': """
        Payroll Work Entries
        """,

    'description': """
        Payroll Work Entries
    """,

    'author': "Glanz",
    'website': "http://www.glanzdesings.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Payroll',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'to_attendance_device', 'hr_payroll', 'hr_attendance','de_hr_payroll_policy'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_payroll_views.xml',
        'views/hr_rest_day_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
