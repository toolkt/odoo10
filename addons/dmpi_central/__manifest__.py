# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Del Monte Philippines Central Database',
    'version' : '1.0',
    'summary': 'Custom Module for Delmonte Philippines',
    'description': """
TODO
CUSTOM FEATURES FOR DMPI CENTRAL

    """,
    'category': 'Custom',
    'sequence': 20,
    'website' : 'http://toolkt.com',
    'depends' : ['base','sale'],
    'demo' : [],
    'data' : [
        'views/sale_sequence.xml',
        'security/ir.model.access.csv',
        'views/central_view.xml',
        'views/database_view.xml',
        'views/database_cmd_view.xml',
        'views/res_partner_view.xml',
    ],
    'test' : [],
    'auto_install': False,
    'installable': True,
}
