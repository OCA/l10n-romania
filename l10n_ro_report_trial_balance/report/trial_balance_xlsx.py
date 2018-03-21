# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class RomaniaReportTrialBalanceXslx(models.AbstractModel):
    _name = 'report.l10n_ro_report_trial_balance_xlsx'
    _inherit = 'report.romania.trial.balance.abstract_report_xlsx'

    def _get_report_company_name(self, report):
        comp_data = report.company_id.name.upper() + '\n'
        comp_data += report.company_id.partner_id._display_address(
            without_company=True) + '\n'
        comp_data += \
            report.company_id.vat + '\n' if report.company_id.vat else ''
        comp_data += \
            report.company_id.partner_id.nrc + '\n' \
            if report.company_id.partner_id.nrc else ''
        return comp_data

    def _get_report_name(self):
        return _('Trial Balance')

    def _get_report_columns(self, report):
        return {
            0: {'header': _('Code'), 'field': 'code',
                'width': 10},
            1: {'header': _('Name'), 'field': 'name', 'width': 100},
            2: {'header': _('Opening Debit'),
                'field': 'debit_opening',
                'type': 'amount',
                'width': 14},
            3: {'header': _('Opening Credit'),
                'field': 'credit_opening',
                'type': 'amount',
                'width': 14},
            4: {'header': _('Initial Debit'),
                'field': 'debit_initial',
                'type': 'amount',
                'width': 14},
            5: {'header': _('Initital Credit'),
                'field': 'credit_initial',
                'type': 'amount',
                'width': 14},
            6: {'header': _('Current Debit'),
                'field': 'debit',
                'type': 'amount',
                'width': 14},
            7: {'header': _('Current Credit'),
                'field': 'credit',
                'type': 'amount',
                'width': 14},
            8: {'header': _('Total Debit'),
                'field': 'debit_total',
                'type': 'amount',
                'width': 14},
            9: {'header': _('Total Credit'),
                'field': 'credit_total',
                'type': 'amount',
                'width': 14},
            10: {'header': _('Balance Debit'),
                 'field': 'debit_balance',
                 'type': 'amount',
                 'width': 14},
            11: {'header': _('Balance Credit'),
                 'field': 'credit_balance',
                 'type': 'amount',
                 'width': 14}}

    def _get_report_filters(self, report):
        return [
            [_('Date from'), report.date_from],
            [_('Date to'), report.date_to],
            [_('All posted entries'), report.only_posted_moves],
            [_('Hide accounts with 0 balance'),
             report.hide_account_balance_at_0],
            [_('With special accounts'), report.with_special_accounts],
        ]

    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 2

    def _generate_report_content(self, workbook, report):
        # For each line
        self.write_array_header(workbook)
        for line in report.line_account_ids:
            style = {'font_size': 7}
            if line.account_group_id and len(line.code) == 1:
                style = {'font_size': 11,
                         'bold': True,
                         'font_color': 'blue'}
            if line.account_group_id and len(line.code) == 2:
                style = {'font_size': 10,
                         'bold': True,
                         'font_color': 'blue'}
            if line.account_group_id and len(line.code) == 3:
                style = {'font_size': 9,
                         'bold': True,
                         'font_color': 'blue'}
            if line.account_group_id and len(line.code) == 4:
                style = {'font_size': 9,
                         'bold': True,
                         'font_color': 'blue'}
            if line.account_group_id and len(line.code) == 5:
                style = {'font_size': 8,
                         'bold': True,
                         'font_color': 'blue'}
            style.update({'num_format': '#,##0.00'})
            # Write line
            self.write_line(workbook, line, dict(style))
