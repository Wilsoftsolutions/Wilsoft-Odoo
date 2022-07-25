# -*- coding: utf-8 -*-
{
    'name': "Sale Xlsx Report",

    'summary': """This report is design for Sale Xlsx Report""",

    'description': """
This report is design for Sale Xlsx Repor    """,

    'author': "Muhammad Ismail",
    # 'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/wizard_view.xml',
        'views/templates.xml',
    ],
   
}
