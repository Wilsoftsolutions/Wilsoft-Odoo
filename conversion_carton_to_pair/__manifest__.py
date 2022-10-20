# -*- coding: utf-8 -*-
{
    'name': "Conversion Carton To Pair",

    'summary': """This module is design for Conversion Carton To Pair""",

    'description': """This module is design for Conversion Carton To Pair    """,

    'author': "Muhammad Ismail",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/conversion_carton_to_pair.xml',
        'views/views.xml',

    ],
    # only loaded in demonstration mode

}
