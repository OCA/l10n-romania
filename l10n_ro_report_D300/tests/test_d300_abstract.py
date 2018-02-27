# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from . import abstract_test


class TestD300(abstract_test.AbstractTest):
    """
        Technical tests for General Ledger Report.
    """

    def _getReportModel(self):
        return self.env['l10n_ro_report_d300']

    def _getQwebReportName(self):
        return 'l10n_ro_report_D300.l10n_ro_report_d300_qweb'

    def _getXlsxReportName(self):
        return 'l10n_ro_report_d300_xlsx'

    def _getXlsxReportActionName(self):
        return 'l10n_ro_report_D300.' \
               'action_l10n_ro_report_d300_xlsx'

    def _getReportTitle(self):
        return 'Odoo Report'

    def _getBaseFilters(self):
        return {
            'date_from': time.strftime('%Y-%m-01'),
            'date_to': time.strftime('%Y-%m-28'),
            'company_id': self.env.ref('base.main_company').id,
            'tax_detail': True
        }
