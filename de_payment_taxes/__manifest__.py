# -*- coding: utf-8 -*-
{
    'name': "Payment Taxes",

    'summary': """
        Payment Taxes
        """,

    'description': """
        Payment Taxes
    """,

    'author': "Dynexcel",
    'website': "http://www.dynexcel.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '15.0.0.2',

    # any module necessary for this one to work correctly
    'depends': ['base','account','account_accountant','report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/wht_report_wizard.xml',
        'report/wht_tax_report.xml',
        'views/account_payment_register_views.xml',
        'views/account_payment_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
