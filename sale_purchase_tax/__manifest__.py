# -*- coding: utf-8 -*-
{
    'name': "Sale and Purchase Taxes",

    'summary': """this module is design for customer sale tax and purchase tax""",

    'description': """
        this module is design for customer sale tax and purchase tax
    """,

    'author': "Muhammad Ismail",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account_accountant', 'sale', 'purchase'],

    # always loaded
    'data': [
        'views/views.xml',
    ],
}
