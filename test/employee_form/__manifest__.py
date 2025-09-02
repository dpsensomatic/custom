# -*- coding: utf-8 -*-
{
    'name': "Formulario de empleados",

    'summary': "Modulo creado para extender la informacion de los empleados ",

    'description': """
No se jeje
    """,

    'author': "Nico",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customisation',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','contacts','l10n_latam_base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/config_contribution_account.xml',
        'views/employee_form.xml',
        'views/contract_form.xml',
    ],
}

