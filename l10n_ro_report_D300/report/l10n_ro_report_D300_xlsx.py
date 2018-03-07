# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class RomaniaReportD300Xslx(models.AbstractModel):
    _name = 'report.l10n_ro_report_d300_xlsx'
    _inherit = 'report.d300.abstract_report_xlsx'

    def _get_report_name(self):
        return _('Decont TVA - D300')

    def _get_report_columns(self, report):
        return {
            0: {'header': _('Code'), 'field': 'code',
                'type': 'amount', 'width': 5},
            1: {'header': _('Name'), 'field': 'name', 'width': 100},
            2: {'header': _('Net'),
                'field': 'net',
                'type': 'amount',
                'width': 14},
            3: {'header': _('Tax'),
                'field': 'tax',
                'type': 'amount',
                'width': 14},
        }

    def _get_report_filters(self, report):
        return [
            [_('Date from'), report.date_from],
            [_('Date to'), report.date_to],
        ]

    def _get_col_count_filter_name(self):
        return 0

    def _get_col_count_filter_value(self):
        return 2

    def _generate_report_content(self, workbook, report):
        # For each taxtag
        self.write_array_header(workbook)
        for taxtag in report.taxtags_ids:
            # Write taxtag line
            self.write_line(workbook, taxtag, {'bold': True, 'font_size': 12})

            # For each tax if detail taxes
            if report.tax_detail:
                formatline = {'font_color': 'gray',
                              'font_size': 10,
                              'num_format': '#,##0.00'}
                for tax in taxtag.tax_ids:
                    self.write_line(workbook, tax, formatline)
