# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from datetime import date

class account_tax_chart(osv.osv_memory):
    """
    For Chart of taxes
    """
    _name = "account.tax.chart"
    _description = "Account tax chart"
    _columns = {
       'period_id': fields.many2one('account.period', \
                                    'Period',  \
                                    ),
       'target_move': fields.selection([('posted', 'All Posted Entries'),
                                        ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
       'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
    }

    def _get_period(self, cr, uid, context=None):
        """Return default period value"""
        period_ids = self.pool.get('account.period').find(cr, uid, context=context)
        return period_ids and period_ids[0] or False

    def _actual_fiscal_year(self, cr, uid, context=None):
        today = date.today()
        fiscalyear_obj = self.pool.get('account.fiscalyear').search(cr, uid,
                                                                    [('date_start', '<=', today),
                                                                     ('date_stop', '>=', today)],
                                                                    context=context)
        if fiscalyear_obj:
            return fiscalyear_obj[0]

    def onchange_fiscalyear_id(self, cr, uid, ids, fiscalyear_id=False, context=None):
        if not fiscalyear_id:
            return {'domain': {'period_id': [('id', '!=', False)]}}
        # self.period_id = False
        period_ids = self.pool.get('account.period').search(cr, uid, [('fiscalyear_id', '=', fiscalyear_id)],
                                                            context=context)
        return {'value': {'period_id': False},
                'domain': {'period_id': [('id', 'in', period_ids)]}}

    def account_tax_chart_open_window(self, cr, uid, ids, context=None):
        """
        Opens chart of Accounts
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of account chart’s IDs
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_tax_code_tree')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        if data.period_id:
            result['context'] = str({'period_id': data.period_id.id,
                                     'fiscalyear_id': data.fiscalyear_id.id,
                                     'state': data.target_move})
            period_code = data.period_id.code
            result['name'] += period_code and (':' + period_code) or ''
        else:
            result['context'] = str({'state': data.target_move,
                                     'fiscalyear_id': data.fiscalyear_id.id})
        return result

    _defaults = {
        'period_id': _get_period,
        'target_move': 'posted',
        'fiscalyear_id': _actual_fiscal_year,
    }
