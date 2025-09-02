 # -*- coding: utf-8 -*-
{
    'name': "Tipos De Regimen", 

    'summary': "Modulo para añadir los diferentes tipos de contribuyentes",

    'description': """
    Este modulo se hace con la intencion de agregar los diferentes tipos de regimen y que a su vez cada que se seleccione uno, se apliquen sus respectivos impuestos
    """, 

    'author': "Nico", 
    'license': "LGPL-3", 


    'category': 'Customisation', 
    'version': '0.1',

    
    'depends': ["base", "account","sale"],

    
    'data': [
        'security/ir.model.access.csv',
        # 'views/account_account_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/accounting_menu.xml',
        'views/product_template.xml',
        'views/res_partner_views.xml',
        'views/tax_regime_views.xml',
    ], 

    'application': True,
    'installable': True, 
}