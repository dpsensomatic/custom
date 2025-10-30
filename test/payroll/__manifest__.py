# -*- coding: utf-8 -*-
{
    'name': "Nómina",

    'summary': "Gestión de Nómina Colombiana",

    'description': """
Este modulo crea la estructura para la gestion de la nomina ajustada a la legislación Colombiana.
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
        'views/hr_contract_views.xml',
        'views/hr_payroll_menu_views.xml',
        'views/hr_parameters_views.xml',
        'views/hr_payroll_events_views.xml',
        'views/hr_payroll_settlement_views.xml',
        'views/hr_eps_entity_views.xml',
        'views/hr_arl_entity_views.xml',
        'views/hr_pension_fund_views.xml',
        'views/hr_compensation_fund_views.xml',
        'views/hr_payroll_views.xml',
        'views/hr_predeterminated_accounts_views.xml',
    ],
    'installable': True,
    'application': True,
}
