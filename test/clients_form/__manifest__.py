# -*- coding: utf-8 -*-
{
    'name': "clientes personalizado",

    'summary': "Añade nuevos campos a la creacion de clientes",

    'description': """
Añade nuevos campos los cuales se adaptan a las necesidades de la empresa 
    """,

    'author': "Nico",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customisation',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/customers_form.xml',
        'views/account_customer_form.xml',
        # 'data/importance_levels.xml'
    ],

    'installable': True,
    'application': True,
}

