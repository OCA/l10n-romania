# Copyright 2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import time

import xlsxwriter

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestTrialBalanceReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=chart_template_ref)
        group_obj = cls.env["account.group"]
        acc_obj = cls.env["account.account"]

        cls.account1 = acc_obj.create(
            {
                "code": "8999",
                "name": "Account 8999",
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
                "reconcile": True,
            }
        )
        cls.account2 = acc_obj.create(
            {
                "code": "89998",
                "name": "Account 89998",
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
                "reconcile": True,
            }
        )
        cls.account3 = acc_obj.create(
            {
                "code": "99999",
                "name": "Account 99999",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_other_income"
                ).id,
            }
        )

        cls.group1 = group_obj.create({"code_prefix_start": "899", "name": "Group 8"})
        cls.group2 = group_obj.create(
            {
                "code_prefix_start": "89998",
                "name": "Group 89998",
                "parent_id": cls.group1.id,
            }
        )
        cls.group3 = group_obj.create(
            {"code_prefix_start": "9999", "name": "Group 9999"}
        )
        cls.previous_fy_date_start = "2020-01-01"
        cls.previous_fy_date_end = "2020-12-31"
        cls.fy_date_start = "2021-01-01"
        cls.date_start = "2021-02-01"
        cls.date_end = "2021-02-28"

    def _add_move(
        self,
        date,
        receivable_debit,
        receivable_credit,
        income_debit,
        income_credit,
        unaffected_debit=0,
        unaffected_credit=0,
    ):
        move_name = "expense accrual"
        journal = self.env["account.journal"].search(
            [("code", "=", "MISC"), ("company_id", "=", self.env.company.id)]
        )
        move_vals = {
            "journal_id": journal.id,
            "date": date,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": move_name,
                        "debit": receivable_debit,
                        "credit": receivable_credit,
                        "account_id": self.account1.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": move_name,
                        "debit": income_debit,
                        "credit": income_credit,
                        "account_id": self.account3.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": move_name,
                        "debit": unaffected_debit,
                        "credit": unaffected_credit,
                        "account_id": self.account2.id,
                    },
                ),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()

    def _get_report_lines(
        self, hierarchy_on="computed", account_ids=None, hide_account=False
    ):
        company = self.env.user.company_id
        trial_balance = self.env["l10n.ro.report.trial.balance.wizard"].create(
            {
                "date_from": self.date_start,
                "date_to": self.date_end,
                "target_move": "posted",
                "hide_account_at_0": hide_account,
                "hierarchy_on": hierarchy_on,
                "account_ids": account_ids,
                "company_id": company.id,
                "show_off_balance_accounts": True,
            }
        )
        data = trial_balance._prepare_report_trial_balance()
        res_data = self.env[
            "report.l10n_ro_report_trial_balance.trial_balance"
        ]._get_report_values(trial_balance, data)
        return res_data

    def _get_report_xlsx_data(
        self, hierarchy_on="computed", account_ids=None, hide_account=False
    ):
        company = self.env.user.company_id
        trial_balance = self.env["l10n.ro.report.trial.balance.wizard"].create(
            {
                "date_from": self.date_start,
                "date_to": self.date_end,
                "target_move": "posted",
                "hide_account_at_0": hide_account,
                "hierarchy_on": hierarchy_on,
                "account_ids": account_ids,
                "company_id": company.id,
                "show_off_balance_accounts": True,
            }
        )

        self.docs = trial_balance
        data = trial_balance._prepare_report_trial_balance()

        objs = (
            self.env["report.l10n_ro_report_trial_balance_xlsx"]
            .with_context({"active_model": "l10n.ro.report.trial.balance.wizard"})
            ._get_objs_for_report(trial_balance.ids, data)
        )
        workbook = xlsxwriter.Workbook("filename.xlsx")

        self.env["report.l10n_ro_report_trial_balance_xlsx"].with_context(
            {"active_model": "l10n.ro.report.trial.balance.wizard"}
        ).generate_xlsx_report(workbook, data, objs)

        self.docs = data
        return workbook

    def check_account_in_report(self, account_id, trial_balance):
        account_in_report = False
        for account in trial_balance:
            if account["id"] == account_id and account["type"] == "account_type":
                account_in_report = True
                break
        return account_in_report

    def _get_account_lines(self, account_id, trial_balance):
        lines = False
        for account in trial_balance:
            if account["id"] == account_id and account["type"] == "account_type":
                lines = {
                    "debit_opening": account["debit_opening"],
                    "credit_opening": account["credit_opening"],
                    "debit_initial": account["debit_initial"],
                    "credit_initial": account["credit_initial"],
                    "debit": account["debit"],
                    "credit": account["credit"],
                    "debit_total": account["debit_total"],
                    "credit_total": account["credit_total"],
                    "debit_balance": account["debit_balance"],
                    "credit_balance": account["credit_balance"],
                }
        return lines

    def _get_group_lines(self, group_id, trial_balance):
        lines = False
        for group in trial_balance:
            if group["id"] == group_id and group["type"] == "group_type":
                lines = {
                    "debit_opening": group["debit_opening"],
                    "credit_opening": group["credit_opening"],
                    "debit_initial": group["debit_initial"],
                    "credit_initial": group["credit_initial"],
                    "debit": group["debit"],
                    "credit": group["credit"],
                    "debit_total": group["debit_total"],
                    "credit_total": group["credit_total"],
                    "debit_balance": group["debit_balance"],
                    "credit_balance": group["credit_balance"],
                }
        return lines

    def _get_trial_balance_lines(
        self, hierarchy_on="computed", account_ids=None, hide_account=False
    ):
        # Re Generate the trial balance line
        res_data = self._get_report_lines(
            hierarchy_on, account_ids=account_ids, hide_account=hide_account
        )
        lines = {}
        trial_balance = res_data["trial_balance"]
        if not account_ids:
            check_receivable_account = self.check_account_in_report(
                self.account1.id, trial_balance
            )
            self.assertTrue(check_receivable_account)

            check_income_account = self.check_account_in_report(
                self.account3.id, trial_balance
            )
            self.assertTrue(check_income_account)
            if not hide_account:
                check_unaffected_account = self.check_account_in_report(
                    self.account2.id, trial_balance
                )
                self.assertTrue(check_unaffected_account)
        else:
            check_receivable_account = self.check_account_in_report(
                self.account1.id, trial_balance
            )
            self.assertTrue(check_receivable_account)

        # Check the initial and final balance
        lines["receivable"] = self._get_account_lines(self.account1.id, trial_balance)
        lines["income"] = self._get_account_lines(self.account3.id, trial_balance)
        lines["unaffected"] = self._get_account_lines(self.account2.id, trial_balance)
        lines["group1"] = self._get_group_lines(self.group1.id, trial_balance)
        lines["group3"] = self._get_group_lines(self.group3.id, trial_balance)
        return lines

    def test_00_account_group(self):
        self.assertEqual(len(self.group1.compute_account_ids.ids), 2)
        self.assertEqual(len(self.group3.compute_account_ids.ids), 1)

    def test_01_account_balance(self):
        # Generate the general ledger line

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the trial balance line
        lines = self._get_trial_balance_lines()

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 0)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 0)
        self.assertEqual(lines["receivable"]["debit_balance"], 1000)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 0)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 0)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 0)
        self.assertEqual(lines["group1"]["debit_balance"], 1000)
        self.assertEqual(lines["group1"]["credit_balance"], 0)

        # Add reversale move of the initial move the first day of fiscal year
        # to check the first day of fiscal year is not used
        # to compute the initial balance

        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line

        lines = self._get_trial_balance_lines()
        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 1000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self.assertEqual(lines["income"]["debit_opening"], 0)
        self.assertEqual(lines["income"]["credit_opening"], 1000)
        self.assertEqual(lines["income"]["debit_initial"], 1000)
        self.assertEqual(lines["income"]["credit_initial"], 0)
        self.assertEqual(lines["income"]["debit"], 0)
        self.assertEqual(lines["income"]["credit"], 0)
        self.assertEqual(lines["income"]["debit_total"], 1000)
        self.assertEqual(lines["income"]["credit_total"], 1000)
        self.assertEqual(lines["income"]["debit_balance"], 0)
        self.assertEqual(lines["income"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 1000)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 0)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 1000)
        self.assertEqual(lines["group1"]["debit_balance"], 0)
        self.assertEqual(lines["group1"]["credit_balance"], 0)

        self.assertEqual(lines["group3"]["debit_opening"], 0)
        self.assertEqual(lines["group3"]["credit_opening"], 1000)
        self.assertEqual(lines["group3"]["debit_initial"], 1000)
        self.assertEqual(lines["group3"]["credit_initial"], 0)
        self.assertEqual(lines["group3"]["debit"], 0)
        self.assertEqual(lines["group3"]["credit"], 0)
        self.assertEqual(lines["group3"]["debit_total"], 1000)
        self.assertEqual(lines["group3"]["credit_total"], 1000)
        self.assertEqual(lines["group3"]["debit_balance"], 0)
        self.assertEqual(lines["group3"]["credit_balance"], 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line
        lines = self._get_trial_balance_lines()

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 1000)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 2000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 1000)

        self.assertEqual(lines["income"]["debit_opening"], 0)
        self.assertEqual(lines["income"]["credit_opening"], 1000)
        self.assertEqual(lines["income"]["debit_initial"], 1000)
        self.assertEqual(lines["income"]["credit_initial"], 0)
        self.assertEqual(lines["income"]["debit"], 1000)
        self.assertEqual(lines["income"]["credit"], 0)
        self.assertEqual(lines["income"]["debit_total"], 2000)
        self.assertEqual(lines["income"]["credit_total"], 1000)
        self.assertEqual(lines["income"]["debit_balance"], 1000)
        self.assertEqual(lines["income"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 1000)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 1000)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 2000)
        self.assertEqual(lines["group1"]["debit_balance"], 0)
        self.assertEqual(lines["group1"]["credit_balance"], 1000)

        self.assertEqual(lines["group3"]["debit_opening"], 0)
        self.assertEqual(lines["group3"]["credit_opening"], 1000)
        self.assertEqual(lines["group3"]["debit_initial"], 1000)
        self.assertEqual(lines["group3"]["credit_initial"], 0)
        self.assertEqual(lines["group3"]["debit"], 1000)
        self.assertEqual(lines["group3"]["credit"], 0)
        self.assertEqual(lines["group3"]["debit_total"], 2000)
        self.assertEqual(lines["group3"]["credit_total"], 1000)
        self.assertEqual(lines["group3"]["debit_balance"], 1000)
        self.assertEqual(lines["group3"]["credit_balance"], 0)

    def test_02_account_balance(self):
        # Generate the general ledger line  for the selected accounts

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the trial balance line for accoun1.id
        lines = self._get_trial_balance_lines(account_ids=[self.account1.id])

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 0)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 0)
        self.assertEqual(lines["receivable"]["debit_balance"], 1000)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line

        lines = self._get_trial_balance_lines(account_ids=[self.account1.id])
        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 1000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line
        lines = self._get_trial_balance_lines(account_ids=[self.account1.id])

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 1000)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 2000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 1000)

    def test_03_account_balance(self):
        # Generate the general ledger line and account groups
        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the trial balance line and account groups in relation
        lines = self._get_trial_balance_lines(hierarchy_on="relation")

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 0)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 0)
        self.assertEqual(lines["receivable"]["debit_balance"], 1000)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 0)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 0)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 0)
        self.assertEqual(lines["group1"]["debit_balance"], 1000)
        self.assertEqual(lines["group1"]["credit_balance"], 0)

        self._add_move(
            date=self.fy_date_start,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line and groups

        lines = self._get_trial_balance_lines(hierarchy_on="relation")
        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 1000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self.assertEqual(lines["income"]["debit_opening"], 0)
        self.assertEqual(lines["income"]["credit_opening"], 1000)
        self.assertEqual(lines["income"]["debit_initial"], 1000)
        self.assertEqual(lines["income"]["credit_initial"], 0)
        self.assertEqual(lines["income"]["debit"], 0)
        self.assertEqual(lines["income"]["credit"], 0)
        self.assertEqual(lines["income"]["debit_total"], 1000)
        self.assertEqual(lines["income"]["credit_total"], 1000)
        self.assertEqual(lines["income"]["debit_balance"], 0)
        self.assertEqual(lines["income"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 1000)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 0)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 1000)
        self.assertEqual(lines["group1"]["debit_balance"], 0)
        self.assertEqual(lines["group1"]["credit_balance"], 0)

        self.assertEqual(lines["group3"]["debit_opening"], 0)
        self.assertEqual(lines["group3"]["credit_opening"], 1000)
        self.assertEqual(lines["group3"]["debit_initial"], 1000)
        self.assertEqual(lines["group3"]["credit_initial"], 0)
        self.assertEqual(lines["group3"]["debit"], 0)
        self.assertEqual(lines["group3"]["credit"], 0)
        self.assertEqual(lines["group3"]["debit_total"], 1000)
        self.assertEqual(lines["group3"]["credit_total"], 1000)
        self.assertEqual(lines["group3"]["debit_balance"], 0)
        self.assertEqual(lines["group3"]["credit_balance"], 0)

        # Add another move at the end day of fiscal year
        # to check that it correctly used on report
        self._add_move(
            date=self.date_end,
            receivable_debit=0,
            receivable_credit=1000,
            income_debit=1000,
            income_credit=0,
        )

        # Re Generate the trial balance line and groups
        lines = self._get_trial_balance_lines(hierarchy_on="relation")

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 1000)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 1000)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 2000)
        self.assertEqual(lines["receivable"]["debit_balance"], 0)
        self.assertEqual(lines["receivable"]["credit_balance"], 1000)

        self.assertEqual(lines["income"]["debit_opening"], 0)
        self.assertEqual(lines["income"]["credit_opening"], 1000)
        self.assertEqual(lines["income"]["debit_initial"], 1000)
        self.assertEqual(lines["income"]["credit_initial"], 0)
        self.assertEqual(lines["income"]["debit"], 1000)
        self.assertEqual(lines["income"]["credit"], 0)
        self.assertEqual(lines["income"]["debit_total"], 2000)
        self.assertEqual(lines["income"]["credit_total"], 1000)
        self.assertEqual(lines["income"]["debit_balance"], 1000)
        self.assertEqual(lines["income"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 1000)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 1000)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 2000)
        self.assertEqual(lines["group1"]["debit_balance"], 0)
        self.assertEqual(lines["group1"]["credit_balance"], 1000)

        self.assertEqual(lines["group3"]["debit_opening"], 0)
        self.assertEqual(lines["group3"]["credit_opening"], 1000)
        self.assertEqual(lines["group3"]["debit_initial"], 1000)
        self.assertEqual(lines["group3"]["credit_initial"], 0)
        self.assertEqual(lines["group3"]["debit"], 1000)
        self.assertEqual(lines["group3"]["credit"], 0)
        self.assertEqual(lines["group3"]["debit_total"], 2000)
        self.assertEqual(lines["group3"]["credit_total"], 1000)
        self.assertEqual(lines["group3"]["debit_balance"], 1000)
        self.assertEqual(lines["group3"]["credit_balance"], 0)

        self.assertEqual(lines["group3"]["credit_balance"], 0)

    def test_04_account_balance(self):
        # Generate the general ledger line and hide accounts that have zero values

        # Add a move at the previous day of the first day of fiscal year
        # to check the initial balance
        self._add_move(
            date=self.previous_fy_date_end,
            receivable_debit=1000,
            receivable_credit=0,
            income_debit=0,
            income_credit=1000,
        )

        # Re Generate the trial balance line
        lines = self._get_trial_balance_lines(
            hierarchy_on="relation", hide_account=True
        )

        # Check the initial and final balance
        self.assertEqual(lines["receivable"]["debit_opening"], 1000)
        self.assertEqual(lines["receivable"]["credit_opening"], 0)
        self.assertEqual(lines["receivable"]["debit_initial"], 0)
        self.assertEqual(lines["receivable"]["credit_initial"], 0)
        self.assertEqual(lines["receivable"]["debit"], 0)
        self.assertEqual(lines["receivable"]["credit"], 0)
        self.assertEqual(lines["receivable"]["debit_total"], 1000)
        self.assertEqual(lines["receivable"]["credit_total"], 0)
        self.assertEqual(lines["receivable"]["debit_balance"], 1000)
        self.assertEqual(lines["receivable"]["credit_balance"], 0)

        self.assertEqual(lines["group1"]["debit_opening"], 1000)
        self.assertEqual(lines["group1"]["credit_opening"], 0)
        self.assertEqual(lines["group1"]["debit_initial"], 0)
        self.assertEqual(lines["group1"]["credit_initial"], 0)
        self.assertEqual(lines["group1"]["debit"], 0)
        self.assertEqual(lines["group1"]["credit"], 0)
        self.assertEqual(lines["group1"]["debit_total"], 1000)
        self.assertEqual(lines["group1"]["credit_total"], 0)
        self.assertEqual(lines["group1"]["debit_balance"], 1000)
        self.assertEqual(lines["group1"]["credit_balance"], 0)

    def test_xlsx(self):
        # Generate xlsx file and check name of first sheet of workbook
        workbook1 = self._get_report_xlsx_data()
        name = "Trial Balance - company_1_data "
        sheet1 = workbook1.worksheets()[0]
        self.assertEqual(sheet1.name, name)

        # Generate xlsx file for account1
        workbook2 = self._get_report_xlsx_data(account_ids=[self.account1.id])
        sheet2 = workbook2.worksheets()[0]
        self.assertEqual(sheet2.name, name)

        # Generate xlsx file and hide account that have values zero
        workbook3 = self._get_report_xlsx_data(hide_account=True)
        sheet3 = workbook3.worksheets()[0]
        self.assertEqual(sheet3.name, name)

        # Generate xlsx file with gorups
        workbook4 = self._get_report_xlsx_data(
            hierarchy_on="relation",
        )
        sheet4 = workbook4.worksheets()[0]
        self.assertEqual(sheet4.name, name)

    def test_wizard_date_range(self):
        trial_balance_wizard = self.env["l10n.ro.report.trial.balance.wizard"]
        date_range = self.env["date.range"]
        self.type = self.env["date.range.type"].create(
            {"name": "Month", "company_id": False, "allow_overlap": False}
        )
        dt = date_range.create(
            {
                "name": "FS2016",
                "date_start": time.strftime("%Y-%m-01"),
                "date_end": time.strftime("%Y-%m-28"),
                "type_id": self.type.id,
            }
        )
        wizard = trial_balance_wizard.create(
            {
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
                "target_move": "posted",
            }
        )
        wizard.onchange_date_range_id()
        self.assertEqual(
            fields.Date.to_string(wizard.date_from), time.strftime("%Y-%m-01")
        )
        self.assertEqual(
            fields.Date.to_string(wizard.date_to), time.strftime("%Y-%m-28")
        )
        wizard._export("qweb-pdf")
        wizard.button_export_html()
        wizard.button_export_pdf()
        wizard.button_export_xlsx()
