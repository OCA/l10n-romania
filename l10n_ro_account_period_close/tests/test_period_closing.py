# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import time

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCurrencyReevaluation(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.per_close_model = cls.env["account.period.closing"]
        cls.wiz_close_model = cls.env["account.period.closing.wizard"]
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

    def test_period_closing(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
        date_from = time.strftime("%Y-%m") + "-01"
        date_to = time.strftime("%Y-%m") + "-28"
        self.exp_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)
        self.inc_closing.close(date_from, date_to)
        self.assertEqual(len(self.exp_closing.move_ids), 1)

    def test_period_closing_wizard(self):
        self.exp_closing._onchange_type()
        self.inc_closing._onchange_type()
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
        wizard = self.wiz_close_model.create(
            {
                "closing_id": self.vat_closing.id,
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
            }
        )
        wizard.onchange_date_range_id()
        self.assertEqual(
            wizard.date_from.strftime("%Y-%m-%d"), time.strftime("%Y-%m-01")
        )
        self.assertEqual(wizard.date_to.strftime("%Y-%m-%d"), time.strftime("%Y-%m-28"))
        wizard.do_close()

    def test_wizard_defaults(self):
        today = fields.Date.from_string(fields.Date.today())
        date_from = today + relativedelta(day=1, months=-1)
        date_to = today + relativedelta(day=1, days=-1)
        wizard = self.wiz_close_model.create({"closing_id": self.vat_closing.id})
        self.assertEqual(
            wizard.date_from.strftime("%Y-%m-%d"), fields.Date.to_string(date_from)
        )
        self.assertEqual(
            wizard.date_to.strftime("%Y-%m-%d"), fields.Date.to_string(date_to)
        )
