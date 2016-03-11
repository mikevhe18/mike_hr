# -*- coding: utf-8 -*-
# © 2013 Michael Telahun Makonnen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, fields, models, _


class HrContract(models.Model):
    _name = 'hr.contract'
    _inherit = ['hr.contract', 'mail.thread', 'ir.needaction_mixin']

    @api.one
    def _get_department(self):
        states = ['pending_done', 'done']
        for contract in self:
            if contract.department_id and contract.state in states:
                self.department_id = contract.department_id.id
            elif contract.employee_id.department_id:
                self.department_id = contract.employee_id.department_id.id
        
    state = fields.Selection([
                ('draft', 'Draft'),
                ('trial', 'Trial'),
                ('trial_ending', 'Trial Period Ending'),
                ('open', 'Open'),
                ('contract_ending', 'Ending'),
                ('pending_done', 'Pending Termination'),
                ('done', 'Completed')
        ],
        string='State',
        readonly=True,
        default='draft')

    # store this field in the database and trigger a change only if the
    # contract is in the right state: we don't want future changes to an
    # employee's department to impact past contracts that have now ended.
    # Increased priority to override hr_simplify.
    
    department_id = fields.Many2one(
        string='Department',
        compute='_get_department',
        comodel_name='hr.department',
        readonly=True,
        store=True)

    # At contract end this field will hold the job_id, and the
    # job_id field will be set to null so that modules that
    # reference job_id don't include deactivated employees.

    end_job_id = fields.Many2one(
        string='Job Title',
        comodel_name='hr.job',
        readonly=True)
        
    # The following are redefined again to make them editable only in
    # certain states
    
    employee_id = fields.Many2one(
        string='Employee',
        comodel_name='hr.employee',
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        })

    type_id = fields.Many2one(
        string='Contract Type',
        comodel_name='hr.contract.type',
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        })
        
    date_start = fields.Date(
        string='Start Date',
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        })
    
    wage = fields.Float(
        string='Wage',
        digits=(16, 2),
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        },
        help='Basic Salary of the employee')

    _track = {
        'state': {
            'hr_contract_state.mt_alert_trial_ending': (
                lambda s, cr, u, o, c=None: o['state'] == 'trial_ending'),
            'hr_contract_state.mt_alert_open': (
                lambda s, cr, u, o, c=None: o['state'] == 'open'),
            'hr_contract_state.mt_alert_contract_ending': (
                lambda s, cr, u, o, c=None: o['state'] == 'contract_ending'),
        },
    }

    def _needaction_domain_get(self, cr, uid, context=None):

        users_obj = self.pool.get('res.users')
        domain = []

        if users_obj.has_group(cr, uid, 'base.group_hr_manager'):
            domain = [
                ('state', 'in', ['draft', 'contract_ending', 'trial_ending'])]
            return domain

        return False

    def onchange_job(self, cr, uid, ids, job_id, context=None):

        import logging
        _l = logging.getLogger(__name__)
        _l.warning('hr_contract_state: onchange_job()')
        res = False
        if isinstance(ids, (int, long)):
            ids = [ids]
        if ids:
            contract = self.browse(cr, uid, ids[0], context=None)
            if contract.state != 'draft':
                return res
        return super(hr_contract, self).onchange_job(
            cr, uid, ids, job_id, context=context
        )

    def condition_trial_period(self, cr, uid, ids, context=None):

        for contract in self.browse(cr, uid, ids, context=context):
            if not contract.trial_date_start:
                return False
        return True

    def try_signal_ending_contract(self, cr, uid, context=None):

        d = datetime.now().date() + relativedelta(days=+30)
        ids = self.search(cr, uid, [
            ('state', '=', 'open'),
            ('date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ], context=context)
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self.browse(cr, uid, ids, context=context):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_ending_contract', cr
            )

    def try_signal_contract_completed(self, cr, uid, context=None):
        d = datetime.now().date()
        ids = self.search(cr, uid, [
            ('state', '=', 'open'),
            ('date_end', '<', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ], context=context)
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self.browse(cr, uid, ids, context=context):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_pending_done', cr
            )

    def try_signal_ending_trial(self, cr, uid, context=None):

        d = datetime.now().date() + relativedelta(days=+10)
        ids = self.search(cr, uid, [
            ('state', '=', 'trial'),
            ('trial_date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ], context=context)
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self.browse(cr, uid, ids, context=context):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_ending_trial', cr
            )

    def try_signal_open(self, cr, uid, context=None):

        d = datetime.now().date() + relativedelta(days=-5)
        ids = self.search(cr, uid, [
            ('state', '=', 'trial_ending'),
            ('trial_date_end', '<=', d.strftime(
                DEFAULT_SERVER_DATE_FORMAT))
        ], context=context)
        if len(ids) == 0:
            return

        wkf = netsvc.LocalService('workflow')
        for contract in self.browse(cr, uid, ids, context=context):
            wkf.trg_validate(
                uid, 'hr.contract', contract.id, 'signal_open', cr
            )

    def onchange_start(self, cr, uid, ids, date_start, context=None):
        return {
            'value': {
                'trial_date_start': date_start,
            },
        }

    def state_trial(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'trial'}, context=context)
        return True

    def state_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'open'}, context=context)
        return True

    def state_pending_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'pending_done'}, context=context)
        return True

    def state_done(self, cr, uid, ids, context=None):
        for i in ids:
            data = self.read(
                cr, uid, i, ['date_end', 'job_id'], context=context)
            vals = {'state': 'done',
                    'date_end': False,
                    'job_id': False,
                    'end_job_id': data['job_id'][0]}

            if data.get('date_end', False):
                vals['date_end'] = data['date_end']
            else:
                vals['date_end'] = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

            self.write(cr, uid, ids, vals, context=context)
        return True
