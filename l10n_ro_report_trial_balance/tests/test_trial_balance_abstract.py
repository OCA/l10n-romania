# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from . import abstract_test


class TestTrialBalance(abstract_test.AbstractTest):
    """
        Technical tests for Trial Balance Report.
    """

    def _getReportModel(self):
        return self.env['l10n_ro_report_trial_balance']

    def _getQwebReportName(self):
        return 'l10n_ro_report_trial_balance.l10n_ro_report_trial_balance_qweb'

    def _getXlsxReportName(self):
        return 'l10n_ro_report_trial_balance_xlsx'

    def _getXlsxReportActionName(self):
        return 'l10n_ro_report_trial_balance.' \
               'action_l10n_ro_report_trial_balance_xlsx'

    def _getReportTitle(self):
        return 'Odoo Report'

    def _getBaseFilters(self):
        return {
            'date_from': time.strftime('%Y-%m-01'),
            'date_to': time.strftime('%Y-%m-28'),
            'company_id': self.env.ref('base.main_company').id
        }

    def _getAdditionalFiltersToBeTested(self):
        return [
            {'only_posted_moves': True},
            {'hide_account_balance_at_0': True},
            {'with_special_accounts': True},
            {'only_posted_moves': True, 'hide_account_balance_at_0': True},
            {'only_posted_moves': True, 'with_special_accounts': True},
            {'hide_account_balance_at_0': True, 'with_special_accounts': True},
            {
                'only_posted_moves': True,
                'hide_account_balance_at_0': True,
                'with_special_accounts': True
            },
        ]
