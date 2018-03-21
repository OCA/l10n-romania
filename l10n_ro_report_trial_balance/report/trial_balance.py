# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class RomaniaTrialBalanceReport(models.TransientModel):
    """ Here, we just define class fields.
    For methods, go more bottom at this file.

    The class hierarchy is :
    * RomaniaTrialBalanceReport
    ** RomaniaTrialBalanceReportAccount
    """

    _name = 'l10n_ro_report_trial_balance'

    # Filters fields, used for data computation
    date_from = fields.Date()
    date_to = fields.Date()
    only_posted_moves = fields.Boolean()
    hide_account_balance_at_0 = fields.Boolean()
    with_special_accounts = fields.Boolean()
    company_id = fields.Many2one(comodel_name='res.company')
    account_ids = fields.Many2many(comodel_name='account.account')

    # Data fields, used to browse report data
    line_account_ids = fields.One2many(
        comodel_name='l10n_ro_report_trial_balance_account',
        inverse_name='report_id'
    )


class RomaniaTrialBalanceAccountReport(models.TransientModel):
    _name = 'l10n_ro_report_trial_balance_account'
    _order = 'code ASC, name ASC'

    report_id = fields.Many2one(
        comodel_name='l10n_ro_report_trial_balance',
        ondelete='cascade',
        index=True
    )

    # Data fields, used to keep link with real object
    account_id = fields.Many2one(
        'account.account',
        index=True
    )

    account_group_id = fields.Many2one(
        'account.group',
        index=True
    )

    # Data fields, used for report display
    code = fields.Char()
    name = fields.Char()

    debit_opening = fields.Float(digits=(16, 2))
    credit_opening = fields.Float(digits=(16, 2))
    debit_initial = fields.Float(digits=(16, 2))
    credit_initial = fields.Float(digits=(16, 2))
    debit = fields.Float(digits=(16, 2))
    credit = fields.Float(digits=(16, 2))
    debit_total = fields.Float(digits=(16, 2))
    credit_total = fields.Float(digits=(16, 2))
    debit_balance = fields.Float(digits=(16, 2))
    credit_balance = fields.Float(digits=(16, 2))

    # Data fields, used to browse report data
    account_ids = fields.Many2many(comodel_name='account.account')


class RomaniaTrialBalanceComputeReport(models.TransientModel):
    """ Here, we just define methods.
    For class fields, go more top at this file.
    """

    _inherit = 'l10n_ro_report_trial_balance'

    @api.multi
    def print_report(self, report_type='qweb'):
        self.ensure_one()
        context = dict(self.env.context)
        if report_type == 'xlsx':
            report_name = 'l10n_ro_report_trial_balance_xlsx'
        else:
            report_name = \
                'l10n_ro_report_trial_balance.' \
                'l10n_ro_report_trial_balance_qweb'
        action = self.env['ir.actions.report'].search(
            [('report_name', '=', report_name),
             ('report_type', '=', report_type)], limit=1)
        return action.with_context(context).report_action(self)

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        report = self.browse(context.get('active_id'))
        if report:
            rcontext['o'] = report
            result['html'] = self.env.ref(
                'l10n_ro_report_trial_balance.'
                'l10n_ro_report_trial_balance').render(
                    rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(given_context)._get_html()

    @api.multi
    def compute_data_for_report(self):
        self.ensure_one()
        self._inject_account_lines()
        self._compute_account_group_values()
        # Refresh cache because all data are computed with SQL requests
        self.refresh()

    def _inject_account_lines(self):
        """Inject report values for report_trial_balance_account"""
        date_from = fields.Date.from_string(self.date_from)
        fy_start_date = fields.Date.to_string(
            date_from + relativedelta(day=1, month=1))
        if self.only_posted_moves:
            states = "'posted'"
        else:
            states = "'draft', 'posted'"
        if self.account_ids:
            accounts = self.account_ids
        else:
            accounts = self.env['account.account'].search(
                [('company_id', '=', self.company_id.id)])
        if not self.with_special_accounts:
            sp_acc_type = self.env.ref(
                'l10n_ro.data_account_type_not_classified')
            if sp_acc_type:
                accounts = accounts.filtered(
                    lambda a: a.user_type_id.id != sp_acc_type.id)
        query_inject_account = """
INSERT INTO
    l10n_ro_report_trial_balance_account
    (
    report_id,
    create_uid,
    create_date,
    account_id,
    code,
    name,
    debit_opening,
    credit_opening,
    debit_initial,
    credit_initial,
    debit,
    credit,
    debit_total,
    credit_total,
    debit_balance,
    credit_balance)
SELECT
    %s AS report_id,
    %s AS create_uid,
    NOW() AS create_date,
    accounts.*,
    CASE WHEN accounts.debit_total > accounts.credit_total
        THEN accounts.debit_total - accounts.credit_total
        ELSE 0
    END AS debit_balance,
    CASE WHEN accounts.credit_total > accounts.debit_total
        THEN accounts.credit_total - accounts.debit_total
        ELSE 0
    END AS credit_balance
FROM
    (
    SELECT
        acc.id, acc.code, acc.name,
        coalesce(sum(open.debit),0) AS debit_opening,
        coalesce(sum(open.credit),0) AS credit_opening,
        coalesce(sum(init.debit),0) AS debit_initial,
        coalesce(sum(init.credit),0) AS credit_initial,
        coalesce(sum(current.debit),0) AS debit,
        coalesce(sum(current.credit),0) AS credit,
        coalesce(sum(open.debit),0) + coalesce(sum(init.debit),0) +
            coalesce(sum(current.debit),0) AS debit_total,
        coalesce(sum(open.credit),0) + coalesce(sum(init.credit),0) +
            coalesce(sum(current.credit),0) AS credit_total
    FROM
        account_account acc
        LEFT OUTER JOIN account_move_line AS open
            ON open.account_id = acc.id AND open.date < %s
        LEFT OUTER JOIN account_move_line AS init
            ON init.account_id = acc.id AND init.date >= %s AND init.date < %s
        LEFT OUTER JOIN account_move_line AS current
            ON current.account_id = acc.id AND current.date >= %s
                AND current.date <= %s
        LEFT JOIN account_move AS move
            ON open.move_id = move.id AND move.state in (%s)
        LEFT JOIN account_move AS init_move
            ON init.move_id = init_move.id AND init_move.state in (%s)
        LEFT JOIN account_move AS current_move
            ON current.move_id = current_move.id AND current_move.state in (%s)
    WHERE acc.id in %s
    GROUP BY acc.id
    ORDER BY acc.code) as accounts"""
        query_inject_account_params = (
            self.id,
            self.env.uid,
            fy_start_date,
            fy_start_date, self.date_from,
            self.date_from, self.date_to,
            states,
            states,
            states,
            accounts._ids,
        )
        self.env.cr.execute(query_inject_account, query_inject_account_params)

    def _compute_account_group_values(self):
        if not self.account_ids:
            acc_res = self.line_account_ids
            groups = self.env['account.group'].search(
                [('code_prefix', '!=', False)])
            for group in groups:
                accounts = acc_res.filtered(
                    lambda a: a.account_id.id in
                    group.compute_account_ids.ids)
                if self.hide_account_balance_at_0:
                    accounts = accounts.filtered(
                        lambda a: a.debit_balance != 0 or
                        a.credit_balance != 0)
                if accounts:
                    newdict = {
                        'report_id': self.id,
                        'account_group_id': group.id,
                        'code': group.code_prefix,
                        'name': group.name,
                        'debit_opening': sum(
                            acc.debit_opening for acc in accounts),
                        'credit_opening': sum(
                            acc.credit_opening for acc in accounts),
                        'debit_initial': sum(
                            acc.debit_initial for acc in accounts),
                        'credit_initial': sum(
                            acc.credit_initial for acc in accounts),
                        'debit': sum(
                            acc.debit for acc in accounts),
                        'credit': sum(
                            acc.credit for acc in accounts),
                        'debit_total': sum(
                            acc.debit_total for acc in accounts),
                        'credit_total': sum(
                            acc.credit_total for acc in accounts),
                        'debit_balance': sum(
                            acc.debit_balance for acc in accounts),
                        'credit_balance': sum(
                            acc.credit_balance for acc in accounts),
                    }
                    self.env['l10n_ro_report_trial_balance_account'].create(
                        newdict)
