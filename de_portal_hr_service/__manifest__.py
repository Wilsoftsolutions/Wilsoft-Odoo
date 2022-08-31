# -*- coding: utf-8 -*-
{
    'name': "Employee Self Service",

    'summary': """
           Employee Self Service
        """,

    'description': """
          Employee Self Service
    """,
    'author': "dynexcel",
    'website': "https://www.dynexcel.com",
    'category': 'Uncategorized',
    'depends': ['portal','hr','rating','base','hr','hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_service_menu.xml',
        'views/hr_service_views.xml',
        'views/hr_approval_request_views.xml',
        'views/hr_approval_request_template.xml',
        'views/hr_employee_views.xml',
        'views/hr_services_templates.xml',
        'views/hr_emp_type_views.xml',
        'views/hr_service_web_templates.xml',   
    ],
   
}
