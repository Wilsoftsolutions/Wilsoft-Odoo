# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "POS FBR Connector",
    "author": "Dynexcel",
    "website": "https://www.dynexcel.com",
    "version": "14.0.1.1",
    "category": "Point Of Sale",
    "summary": "POS FBR Connector",
    "description": """  
    POS FBR Connector
    """,
    "depends": ['point_of_sale'],
    
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
        'views/product_views.xml',
#         "data/scheduled_action.xml",
        "views/templates.xml",
        "views/fbr_data_view.xml",
        'data/data.xml',
    ],    
    "qweb": ["static/src/xml/*.xml"],
    'images': ['static/description/banner.jpg'],
    "installable": True,
    "auto_install": False,
    "application": True,        
}