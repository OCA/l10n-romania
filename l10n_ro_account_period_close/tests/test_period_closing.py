# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import time

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPeriodClosing(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.per_close_model = cls.env["l10n.ro.account.period.closing"]
        cls.wiz_close_model = cls.env["l10n.ro.account.period.closing.wizard"]
        cls.company = company = cls.env.company

        default_account_revenue = cls.company_data["default_account_revenue"]
        default_account_expense = cls.company_data["default_account_expense"]
        default_account_receivable = cls.company_data["default_account_receivable"]
        default_account_payable = cls.company_data["default_account_payable"]
        default_account_tax_sale = company.account_sale_tax_id.mapped(
            "invoice_repartition_line_ids.account_id"
        )
        default_account_tax_purchase = company.account_purchase_tax_id.mapped(
            "invoice_repartition_line_ids.account_id"
        )

        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.debit_acc = cls.env["account.account"].create(
            {
                "name": "DEBIT ACC",
                "code": "DEBITACC",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_liabilities"
                ).id,
                "reconcile": True,
                "company_id": cls.company.id,
            }
        )
        cls.credit_acc = cls.env["account.account"].create(
            {
                "name": "CREDIT ACC",
                "code": "CREDITACC",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_liabilities"
                ).id,
                "reconcile": True,
                "company_id": cls.company.id,
            }
        )
        cls.vat_close_debit = cls.env["account.account"].create(
            {
                "name": "VAT CLOSE DEBIT",
                "code": "VATCLOSEDEBIT",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
                "company_id": cls.company.id,
            }
        )
        cls.vat_close_credit = cls.env["account.account"].create(
            {
                "name": "VAT CLOSE CREDIT",
                "code": "VATCLOSECREDIT",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
                "company_id": cls.company.id,
            }
        )
        cls.tax_base_amount_account = cls.env["account.account"].create(
            {
                "name": "TAX_BASE",
                "code": "TBASE",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
                "company_id": cls.company.id,
            }
        )
        cls.exp_closing = cls.per_close_model.create(
            {
                "name": "Closing Expenses",
                "type": "expense",
                "journal_id": cls.misc_journal.id,
                "debit_account_id": cls.debit_acc.id,
                "credit_account_id": cls.credit_acc.id,
            }
        )
        cls.inc_closing = cls.per_close_model.create(
            {
                "name": "Closing Incomes",
                "type": "income",
                "journal_id": cls.misc_journal.id,
                "close_result": True,
                "debit_account_id": cls.debit_acc.id,
                "credit_account_id": cls.credit_acc.id,
            }
        )
        cls.vat_closing = cls.per_close_model.create(
            {
                "name": "Closing VAT",
                "type": "selected",
                "account_ids": [
                    (
                        6,
                        0,
                        [default_account_tax_sale.id, default_account_tax_purchase.id],
                    )
                ],
                "journal_id": cls.misc_journal.id,
                "debit_account_id": cls.vat_close_debit.id,
                "credit_account_id": cls.vat_close_credit.id,
            }
        )

        cls.test_move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string(time.strftime("%Y-%m") + "-01"),
                "line_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "revenue line 2",
                            "account_id": default_account_revenue.id,
                            "debit": 0.0,
                            "credit": 1000.0,
                            "tax_ids": [(6, 0, company.account_sale_tax_id.ids)],
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "name": "tax line",
                            "account_id": default_account_tax_sale.id,
                            "debit": 0.0,
                            "credit": 150.0,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "name": "client line",
                            "account_id": default_account_receivable.id,
                            "debit": 1150,
                            "credit": 0.0,
                        },
                    ),
                ],
            }
        )
        cls.test_move.action_post()

        cls.test_move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string(time.strftime("%Y-%m") + "-01"),
                "line_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "cost line 2",
                            "account_id": default_account_expense.id,
                            "debit": 100.0,
                            "credit": 0.0,
                            "tax_ids": [(6, 0, company.account_purchase_tax_id.ids)],
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "name": "tax line",
                            "account_id": default_account_tax_purchase.id,
                            "debit": 15.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "name": "ventor line",
                            "account_id": default_account_payable.id,
                            "debit": 0.0,
                            "credit": 115.0,
                        },
                    ),
                ],
            }
        )
        cls.test_move.action_post()

    def test_period_closing_onchange_type(self):
        inc_accounts = exp_accounts = self.env["account.account"]
        acc_type = self.env.ref("account.data_account_type_expenses").id
        if acc_type:
            exp_accounts = self.env["account.account"].search(
                [
                    ("user_type_id", "=", acc_type),
                    ("company_id", "=", self.company.id),
                ]
            )
        acc_type = self.env.ref("account.data_account_type_revenue").id
        if acc_type:
            inc_accounts = self.env["account.account"].search(
                [
                    ("user_type_id", "=", acc_type),
                    ("company_id", "=", self.company.id),
                ]
            )
        self.exp_closing._onchange_type()
        self.assertEqual(self.exp_closing.account_ids, exp_accounts)
        self.inc_closing._onchange_type()
        self.assertEqual(self.inc_closing.account_ids, inc_accounts)

    def test_period_closing_get_accounts(self):

        account_expense = self.company_data["default_account_expense"]
        expected_exp_account = [
            {
                "credit": 0.0,
                "debit": 100.0,
                "balance": 100.0,
                "id": account_expense.id,
                "code": account_expense.code,
                "name": account_expense.name,
            }
        ]
        account_revenue = self.company_data["default_account_revenue"]
        expected_inc_account = [
            {
                "credit": 1000.0,
                "debit": 0.0,
                "balance": -1000.0,
                "id": account_revenue.id,
                "code": account_revenue.code,
                "name": account_revenue.name,
            }
        ]
        account_sale_tax = self.company.account_sale_tax_id.mapped(
            "invoice_repartition_line_ids.account_id"
        )
        account_purchase_tax = self.company.account_purchase_tax_id.mapped(
            "invoice_repartition_line_ids.account_id"
        )
        expected_vat_account = [
            {
                "credit": 150.0,
                "debit": 0.0,
                "balance": -150.0,
                "id": account_sale_tax.id,
                "code": account_sale_tax.code,
                "name": account_sale_tax.name,
            },
            {
                "credit": 0.0,
                "debit": 15.0,
                "balance": 15.0,
                "id": account_purchase_tax.id,
                "code": account_purchase_tax.code,
                "name": account_purchase_tax.name,
            },
        ]
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_from = fields.Date.from_string(time.strftime("%Y-%m") + "-01")
        date_to = fields.Date.from_string(time.strftime("%Y-%m") + "-28")
        ctx = self.env.context.copy()
        ctx.update(
            {
                "strict_range": True,
                "state": "posted",
                "date_from": date_from,
                "date_to": date_to,
                "company_id": self.company.id,
            }
        )
        exp_account_res = self.exp_closing.with_context(ctx)._get_accounts(
            self.exp_closing.account_ids, "not_zero"
        )
        inc_account_res = self.inc_closing.with_context(ctx)._get_accounts(
            self.inc_closing.account_ids, "not_zero"
        )
        vat_account_res = self.vat_closing.with_context(ctx)._get_accounts(
            self.vat_closing.account_ids, "all"
        )
        self.assertEqual(expected_exp_account, exp_account_res)
        self.assertEqual(expected_inc_account, inc_account_res)
        self.assertEqual(expected_vat_account, vat_account_res)

    def test_period_closing_move_ids(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_from = time.strftime("%Y-%m") + "-01"
        date_to = time.strftime("%Y-%m") + "-28"
        self.exp_closing.close(date_from=date_from, date_to=date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)
        self.inc_closing.close(date_from=date_from, date_to=date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)

    def test_period_closing_wizard_defaults(self):
        today = fields.Date.from_string(fields.Date.today())
        date_from = today + relativedelta(day=1, months=-1)
        date_to = today + relativedelta(day=1, days=-1)
        wizard = self.wiz_close_model.create({"closing_id": self.vat_closing.id})
        self.assertEqual(wizard._get_default_date_from(), date_from)
        self.assertEqual(wizard._get_default_date_to(), date_to)

        self.assertEqual(
            wizard.date_from.strftime("%Y-%m-%d"), fields.Date.to_string(date_from)
        )
        self.assertEqual(
            wizard.date_to.strftime("%Y-%m-%d"), fields.Date.to_string(date_to)
        )
