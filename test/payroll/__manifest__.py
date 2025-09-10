# -*- coding: utf-8 -*-
{
    'name': "Nomina",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customisation',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payroll_menu_views.xml',
        'views/hr_parameters_views.xml',
        'views/hr_payroll_events_views.xml',
        'views/hr_payroll_settlement_views.xml',
        'views/hr_payroll_views.xml',
    ],
}
