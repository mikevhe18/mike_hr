# -*- coding: utf-8 -*-
# © 2013 Michael Telahun Makonnen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Manage Employee Contracts',
    "version": "8.0.1.0.0",
    'category': 'Generic Modules/Human Resources',
    'author': "Michael Telahun Makonnen,Odoo Community Association (OCA)",
    'website': 'http://miketelahun.wordpress.com',
    'license': 'AGPL-3',
    'depends': [
        'hr_contract',
        'hr_contract_init',
    ],
    "external_dependencies": {
        'python': ['dateutil'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract_cron.xml',
        'views/hr_contract_data.xml',
        'workflow/hr_contract_workflow.xml',
        'views/hr_contract_view.xml',
    ],
    "installable": True,
}
