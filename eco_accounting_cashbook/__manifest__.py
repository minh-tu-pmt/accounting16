# -*- coding: utf-8 -*-
{
    'name': "Báo cáo sổ quỹ tiền mặt",

    'summary': """
        Báo cáo sổ quỹ tiền mặt""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_accountant'],
    'data':[
        'security/ir.model.access.csv',
        'views/account_book_report_view.xml',
        'views/menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'eco_accounting_cashbook/static/src/js/input_autocomplete.js',
            'eco_accounting_cashbook/static/src/js/report_cash_book.js',
            'eco_accounting_cashbook/static/src/js/report_registry.js',
            'eco_accounting_cashbook/static/src/xml/cash_book.xml',
            'eco_accounting_cashbook/static/src/xml/input_complete.xml',
        ],
    },
    'auto_install': True,
}
