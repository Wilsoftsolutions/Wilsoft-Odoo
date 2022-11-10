# -*- coding: utf-8 -*-
{
    'name': "Inventory Ageing Report",

    'summary': """
        This is design for Inventory Ageing Report """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Ismail",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/inventory_ageing_report.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode

}
