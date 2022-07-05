# -*- coding: utf-8 -*-
{
    'name': "Inventory Xlsx Report",
    'summary': """This module is design form Inventory Xlsx Report""",
    'description': """This module is design form Inventory Xlsx Report    """,
    'author': "Muhammad Ismail",
    'website': "",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'stock', 'report_xlsx'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'wizard/wizard_view.xml',
    ],

}
