# -*- coding: utf-8 -*-
# © 2013 Michael Telahun Makonnen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agp

from datetime import datetime, timedelta

from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _


class ContractInit(models.Model):
    _name = 'hr.contract.init'
    _description = 'Initial Contract Settings'
    _inherit = 'ir.needaction_mixin'
    _order = 'date desc'
    
    name = fields.Char(
        string='Name',
        size=64,
        required=True,
        readonly=True,
        states={'draft':[('readonly',False)]})
        
    date = fields.Date(
        string='Effective Date',
        required=True,
        readonly=True,
        states={'draft':[('readonly',False)]})
        
    wage_ids = fields.One2many(
        string='Starting Wages',
        comodel_name='hr.contract.init.wage',
        inverse_name='contract_init_id',
        readonly=True,
        states={'draft':[('readonly',False)]})
        
    struct_id = fields.Many2one(
        string='Payroll Structure',
        comodel_name='hr.payroll.structure',
        readonly=True,
        states={'draft':[('readonly',False)]})
        
    trial_period = fields.Integer(
        string='Trial Period',
        readonly=True,
        default=0,
        help='Length of Trial Period, in days',
        states={'draft':[('readonly',False)]})
        
    active = fields.Boolean(
        string='Active',
        default=True)
    
    state = fields.Selection(
        string='State',
        readonly=True,
        default='draft',
        selection=[
            ('draft','Draft'),
            ('confirmed','Confirm'),
            ('approved','Ready To Process'),
            ('proforma','Pro-Forma'),
            ('posted','Posted'),
            ('cancelled','Cancelled')])

    # Return records with latest date first

    def _needaction_domain_get(self, cr, uid, context=None):

        users_obj = self.pool.get('res.users')

        if users_obj.has_group(cr, uid, 'base.group_hr_director'):
            domain = [('state', 'in', ['draft'])]
            return domain

        return False

    def unlink(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]
        data = self.read(cr, uid, ids, ['state'], context=context)
        for d in data:
            if d['state'] in ['approve', 'decline']:
                raise orm.except_orm(
                    _('Error'),
                    _('You may not a delete a record that is not in a '
                      '"Draft" state')
                )
        return super(contract_init, self).unlink(cr, uid, ids, context=context)

    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
        }, context=context)
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_delete(uid, 'hr.contract.init', i, cr)
            wf_service.trg_create(uid, 'hr.contract.init', i, cr)
        return True

    def state_approve(self, cr, uid, ids, context=None):

        self.write(cr, uid, ids, {'state': 'approve'}, context=context)
        return True

    def state_decline(self, cr, uid, ids, context=None):

        self.write(cr, uid, ids, {'state': 'decline'}, context=context)
        return True


class InitWage(models.Model):
    _name = 'hr.contract.init.wage'
    _description = 'Starting Wages'
    
    job_id = fields.Many2one(
        string='Job',
        comodel_name='hr.job')
        
    starting_wage = fields.Float(
        string='Starting Wage',
        digits_compute=dp.get_precision('Payroll'),
        required=True)
        
    is_default = fields.Boolean(
        string='Use as Default',
        help='Use as default wage')
        
    contract_init_id = fields.Many2one(
        string='Contract Settings',
        comodel_name='hr.contract.init')
        
    category_ids = fields.Many2many(
        string='Tags',
        comodel_name='hr.employee.category',
        relation='contract_init_category_rel',
        column1='contract_init_id',
        column2='category_id')

    def _rec_message(self, cr, uid, ids, context=None):
        return _('A Job Position cannot be referenced more than once in a '
                 'Contract Settings record.')

    _sql_constraints = [
        ('unique_job_cinit', 'UNIQUE(job_id,contract_init_id)', _rec_message),
    ]

    def unlink(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]
        data = self.read(cr, uid, ids, ['contract_init_id'], context=context)
        for d in data:
            if not d.get('contract_init_id', False):
                continue
            d2 = self.pool.get(
                'hr.contract.init').read(cr, uid, d['contract_init_id'][0],
                                         ['state'], context=context)
            if d2['state'] in ['approve', 'decline']:
                raise orm.except_orm(
                    _('Error'),
                    _('You may not a delete a record that is not in a '
                      '"Draft" state')
                )
        return super(init_wage, self).unlink(cr, uid, ids, context=context)


class HrContract(models.Model):

    _inherit = 'hr.contract'

    def _get_wage(self, cr, uid, context=None, job_id=None):

        res = 0
        default = 0
        init = self.get_latest_initial_values(cr, uid, context=context)
        if job_id:
            catdata = self.pool.get('hr.job').read(
                cr, uid, job_id, ['category_ids'], context=context)
        else:
            catdata = False
        if init is not None:
            for line in init.wage_ids:
                if job_id is not None and line.job_id.id == job_id:
                    res = line.starting_wage
                elif catdata:
                    cat_id = False
                    category_ids = [c.id for c in line.category_ids]
                    for ci in catdata['category_ids']:
                        if ci in category_ids:
                            cat_id = ci
                            break
                    if cat_id:
                        res = line.starting_wage
                if line.is_default and default == 0:
                    default = line.starting_wage
                if res != 0:
                    break
        if res == 0:
            res = default
        return res

    def _get_struct(self, cr, uid, context=None):

        res = False
        init = self.get_latest_initial_values(cr, uid, context=context)
        if init is not None and init.struct_id:
            res = init.struct_id.id
        return res

    def _get_trial_date_start(self, cr, uid, context=None):

        res = False
        init = self.get_latest_initial_values(cr, uid, context=context)
        if init is not None and init.trial_period and init.trial_period > 0:
            res = datetime.now().strftime(OE_DFORMAT)
        return res

    def _get_trial_date_end(self, cr, uid, context=None):

        res = False
        init = self.get_latest_initial_values(cr, uid, context=context)
        if init is not None and init.trial_period and init.trial_period > 0:
            dEnd = datetime.now().date() + timedelta(days=init.trial_period)
            res = dEnd.strftime(OE_DFORMAT)
        return res

    _defaults = {
        'wage': _get_wage,
        'struct_id': _get_struct,
        'trial_date_start': _get_trial_date_start,
        'trial_date_end': _get_trial_date_end,
    }

    def onchange_job(self, cr, uid, ids, job_id, context=None):

        res = False
        if job_id:
            wage = self._get_wage(cr, uid, context=context, job_id=job_id)
            res = {'value': {'wage': wage}}
        return res

    def onchange_trial(self, cr, uid, ids, trial_date_start, context=None):

        res = {'value': {'trial_date_end': False}}

        init = self.get_latest_initial_values(cr, uid, context=context)
        if init is not None and init.trial_period and init.trial_period > 0:
            dStart = datetime.strptime(trial_date_start, OE_DFORMAT)
            dEnd = dStart + timedelta(days=init.trial_period)
            res['value']['trial_date_end'] = dEnd.strftime(OE_DFORMAT)

        return res

    def get_latest_initial_values(self, cr, uid, today_str=None, context=None):
        """Return a record with an effective date before today_str
        but greater than all others
        """

        init_obj = self.pool.get('hr.contract.init')
        if today_str is None:
            today_str = datetime.now().strftime(OE_DFORMAT)
        dToday = datetime.strptime(today_str, OE_DFORMAT).date()

        res = None
        ids = init_obj.search(
            cr, uid, [('date', '<=', today_str), ('state', '=', 'approve')],
            context=context)
        for init in init_obj.browse(cr, uid, ids, context=context):
            d = datetime.strptime(init.date, OE_DFORMAT).date()
            if d <= dToday:
                if res is None:
                    res = init
                elif d > datetime.strptime(res.date, OE_DFORMAT).date():
                    res = init

        return res
