# -*- coding: utf-8 -*-
# © 2013 Michael Telahun Makonnen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agp

{
    'name': 'Contracts - Initial Settings',
    'version': '8.0.1.0.0',
    'author': "Michael Telahun Makonnen <mmakonnen@gmail.com>,Odoo Community Association (OCA)",
    'website': 'http://miketelahun.wordpress.com',
    'category': 'Generic Modules/Human Resources',
    'license': 'AGPL-3',
    'depends': [
        'hr',
        'hr_contract',
        'hr_job_categories',
        'hr_payroll',
        'hr_security',
        'hr_simplify',
    ],
    'data': [
        'security/ir.model.access.csv',
        'workflow/hr_contract_init_workflow.xml',
        'views/hr_contract_view.xml',
    ],
    'installable': True,
}
