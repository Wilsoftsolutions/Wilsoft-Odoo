# -*- coding: utf-8 -*-
{
    'name': "WareHouse Restriction",

    'summary': """
        WareHouse Restriction
       """,

    'description': """
        WareHouse Restriction
    """,

    'author': "Glanz",
    'website': "http://www.glanzdesigns.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'views/user_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
