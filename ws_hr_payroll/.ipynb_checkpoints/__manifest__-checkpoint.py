# -*- coding: utf-8 -*-
{
    'name': "Payroll",

    'summary': """
        Payroll Process Management
        """,

    'description': """
        Payroll Process Management
    """,

    'author': "Wilshire",
    'website': "http://www.wilshire.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Payroll',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'report_xlsx', 'hr_payroll'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
#         'reports/batch_slip_report.xml',
        'views/views.xml',
        'views/portal_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
