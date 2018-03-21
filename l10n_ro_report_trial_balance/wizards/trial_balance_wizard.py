# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat


class RomaniaTrialBalanceReportWizard(models.TransientModel):
    """Trial balance report wizard."""

    _name = "l10n.ro.report.trial.balance.wizard"
    _description = "Romania Trial Balance Report Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        string='Company'
    )
    date_range_id = fields.Many2one(
        comodel_name='date.range',
        string='Date range'
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')],
                                   string='Target Moves',
                                   required=True,
                                   default='posted')
    hide_account_balance_at_0 = fields.Boolean(
        string='Hide account ending balance at 0',
        help='Use this filter to hide accounts '
             'with an ending balance at 0. '
             'If all accounts from an account group have ending balance at 0, '
             'the group will not be printed in the report.')
    with_special_accounts = fields.Boolean(
        'With Special Accounts',
        help="Check this if you want to print classes 8 and 9 of accounts.")
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Filter accounts',
    )

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        """Handle date range change."""
        self.date_from = self.date_range_id.date_start
        self.date_to = self.date_range_id.date_end

    @api.multi
    def button_export_html(self):
        self.ensure_one()
        action = self.env.ref(
            'l10n_ro_report_trial_balance.action_l10n_ro_report_trial_balance')
        vals = action.read()[0]
        context1 = vals.get('context', {})
        if isinstance(context1, pycompat.string_types):
            context1 = safe_eval(context1)
        model = self.env['l10n_ro_report_trial_balance']
        report = model.create(self._prepare_report_trial_balance())
        report.compute_data_for_report()

        context1['active_id'] = report.id
        context1['active_ids'] = report.ids
        vals['context'] = context1
        return vals

    @api.multi
    def button_export_pdf(self):
        self.ensure_one()
        report_type = 'qweb-pdf'
        return self._export(report_type)

    @api.multi
    def button_export_xlsx(self):
        self.ensure_one()
        report_type = 'xlsx'
        return self._export(report_type)

    def _prepare_report_trial_balance(self):
        self.ensure_one()
        accounts = False
        if self.account_ids:
            accounts = self.account_ids
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'only_posted_moves': self.target_move == 'posted',
            'company_id': self.company_id.id,
            'hide_account_balance_at_0': self.hide_account_balance_at_0,
            'with_special_accounts': self.with_special_accounts,
            'account_ids': [(6, 0, accounts.ids if accounts else [])],
        }

    def _export(self, report_type):
        """Default export is PDF."""
        model = self.env['l10n_ro_report_trial_balance']
        report = model.create(self._prepare_report_trial_balance())
        report.compute_data_for_report()
        return report.with_context(landscape=True).print_report(report_type)
