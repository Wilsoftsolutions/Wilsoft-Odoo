# -*- coding: utf-8 -*-
{
    'name': "Sale Order Lead Time",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '1',
    'depends': ['base','report_xlsx','stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'Wizard/sale_order_lead.xml'
    ],

}
