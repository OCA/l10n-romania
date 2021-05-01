# Copyright  2018 Forest and Biomass Romania
# Copyright (C) 2021 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class RomaniaReportTrialBalanceXslx(models.AbstractModel):
    _name = "report.l10n_ro_report_trial_balance_xlsx"
    _description = "Romania - Trial Balance XLSX Report"
    _inherit = "report.a_f_r.report_trial_balance_xlsx"

    def _get_report_columns(self, report):
        return {
            0: {"header": _("Code"), "field": "code", "width": 10},
            1: {"header": _("Name"), "field": "name", "width": 100},
            2: {
                "header": _("Opening Debit"),
                "field": "debit_opening",
                "type": "amount",
                "width": 14,
            },
            3: {
                "header": _("Opening Credit"),
                "field": "credit_opening",
                "type": "amount",
                "width": 14,
            },
            4: {
                "header": _("Initial Debit"),
                "field": "debit_initial",
                "type": "amount",
                "width": 14,
            },
            5: {
                "header": _("Initital Credit"),
                "field": "credit_initial",
                "type": "amount",
                "width": 14,
            },
            6: {
                "header": _("Current Debit"),
                "field": "debit",
                "type": "amount",
                "width": 14,
            },
            7: {
                "header": _("Current Credit"),
                "field": "credit",
                "type": "amount",
                "width": 14,
            },
            8: {
                "header": _("Total Debit"),
                "field": "debit_total",
                "type": "amount",
                "width": 14,
            },
            9: {
                "header": _("Total Credit"),
                "field": "credit_total",
                "type": "amount",
                "width": 14,
            },
            10: {
                "header": _("Balance Debit"),
                "field": "debit_balance",
                "type": "amount",
                "width": 14,
            },
            11: {
                "header": _("Balance Credit"),
                "field": "credit_balance",
                "type": "amount",
                "width": 14,
            },
        }

    def _get_report_filters(self, report):

        return [
            [
                _("Date range filter"),
                _("From: %s To: %s") % (report.date_from, report.date_to),
            ],
            [
                _("Target moves filter"),
                _("All posted entries")
                if report.target_move == "all"
                else _("All entries"),
            ],
            [
                _("Account at 0 filter"),
                _("Hide") if report.hide_account_at_0 else _("Show"),
            ],
            [
                _("Show foreign currency"),
                _("Yes") if report.foreign_currency else _("No"),
            ],
            [
                _("Limit hierarchy levels"),
                _("Level %s" % report.show_hierarchy_level)
                if report.limit_hierarchy_level
                else _("No limit"),
            ],
        ]

    def _get_col_count_filter_value(self):
        return 2

    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.l10n_ro_report_trial_balance.trial_balance"
        ]._get_report_values(report, data)
        trial_balance = res_data["trial_balance"]
        # total_amount = res_data["total_amount"]

        # accounts_data = res_data["accounts_data"]
        hierarchy_on = res_data["hierarchy_on"]

        show_hierarchy_level = res_data["show_hierarchy_level"]
        # foreign_currency = res_data["foreign_currency"]
        limit_hierarchy_level = res_data["limit_hierarchy_level"]

        # Display array header for account lines
        self.write_array_header(report_data)

        # For each account

        for balance in trial_balance:
            if hierarchy_on == "relation":
                if limit_hierarchy_level:
                    if show_hierarchy_level > balance["level"]:
                        # Display account lines
                        self.write_line_from_dict_custom(balance, report_data, workbook)
                else:
                    self.write_line_from_dict_custom(balance, report_data, workbook)
            elif hierarchy_on == "computed":
                if balance["type"] == "account_type":
                    if limit_hierarchy_level:
                        if show_hierarchy_level > balance["level"]:
                            # Display account lines
                            self.write_line_from_dict_custom(
                                balance, report_data, workbook
                            )
                    else:
                        self.write_line_from_dict_custom(balance, report_data, workbook)
            else:
                self.write_line_from_dict_custom(balance, report_data, workbook)

    def write_line_from_dict_custom(self, line_dict, report_data, workbook):
        """Set the format of the xlsx lines for the groups of accounts according to their level"""

        if line_dict["type"] == "group_type":
            if line_dict["level"] == 0:
                report_data["formats"]["custom"] = workbook.add_format(
                    {"bold": True, "bg_color": "#f2f2f2"}
                )
                report_data["formats"]["custom_amount"] = workbook.add_format(
                    {"bold": True, "bg_color": "#f2f2f2"}
                )
            elif line_dict["level"] == 1:
                report_data["formats"]["custom"] = workbook.add_format(
                    {"bold": True, "italic": True}
                )
                report_data["formats"]["custom_amount"] = workbook.add_format(
                    {"bold": True, "italic": True}
                )
            elif line_dict["level"] == 2:
                report_data["formats"]["custom"] = workbook.add_format(
                    {"bold": False, "italic": True}
                )
                report_data["formats"]["custom_amount"] = workbook.add_format(
                    {"italic": True}
                )

        self.write_line_from_dict(line_dict, report_data)

    def write_line_from_dict(self, line_dict, report_data):
        """Write a line on current line"""
        for col_pos, column in report_data["columns"].items():
            value = line_dict.get(column["field"], False)
            cell_type = column.get("type", "string")
            if cell_type == "string":
                if "custom" in report_data["formats"].keys():
                    cell_format = report_data["formats"]["custom"]
                else:
                    cell_format = ""
                if (
                    not isinstance(value, str)
                    and not isinstance(value, bool)
                    and not isinstance(value, int)
                ):
                    value = value and value.strftime("%d/%m/%Y")
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or "", cell_format
                    )
                else:
                    report_data["sheet"].write_string(
                        report_data["row_pos"], col_pos, value or "", cell_format
                    )
            elif cell_type == "amount":
                if "custom_amount" in report_data["formats"].keys():
                    cell_format = report_data["formats"]["custom_amount"]
                else:
                    cell_format = report_data["formats"]["format_amount"]
                report_data["sheet"].write_number(
                    report_data["row_pos"], col_pos, float(value), cell_format
                )

        if "custom_amount" in report_data["formats"].keys():
            report_data["formats"].pop("custom_amount")
        if "custom" in report_data["formats"].keys():
            report_data["formats"].pop("custom")
        report_data["row_pos"] += 1
