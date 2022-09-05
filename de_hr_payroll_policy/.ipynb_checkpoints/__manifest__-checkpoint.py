# -*- coding: utf-8 -*-
{
    'name': "HR Payroll Policy",

    'summary': """   
        HR Payroll Policy""",

    'description': """
        HR Payroll Policy
    """,

    'author': "Dynexcel",
    'website': "http://www.dynexcel.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Employees',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/email_template.xml',
        'views/hr_employee_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/res_company_views.xml',
        'wizard/payroll_summary_wizard.xml',
        'report/payroll_summary_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
