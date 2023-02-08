# -*- coding: utf-8 -*-
{
    'name': "Material Request Report",

    'summary': """
        Material Request Report
        """,

    'description': """
        Material Request Report
    """,

    'author': "Inventory",
    'website': "http://www.glanzdesigns.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Material',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','claimed_form','report_xlsx','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/material_report_wizard.xml',
        'wizard/stock_trans_wizard.xml',
        'wizard/stock_movement_wizard.xml',
        'report/stock_movement_report.xml',
        'report/material_report.xml',
        'report/transfer_report.xml',
        'views/stock_location_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
