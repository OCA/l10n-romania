# ©  2023 Deltatech
# See README.rst file on addons root folder for license details

import time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TesJournalRegisterReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if not chart_template_ref:
            chart_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=chart_template_ref)

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
                            "name": "vendor line",
                            "account_id": default_account_payable.id,
                            "debit": 0.0,
                            "credit": 115.0,
                        },
                    ),
                ],
            }
        )
        cls.test_move.action_post()

        invoices = cls.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "invoice_date": fields.Date.from_string(
                        time.strftime("%Y-%m") + "-01"
                    ),
                    "date": fields.Date.from_string(time.strftime("%Y-%m") + "-01"),
                    "partner_id": cls.partner_a.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 5.0,
                                "price_unit": 1000.0,
                                "tax_ids": [
                                    (6, 0, cls.company_data["default_tax_sale"].ids)
                                ],
                            },
                        )
                    ],
                },
                {
                    "move_type": "out_invoice",
                    "invoice_date": "2021-03-01",
                    "date": "2021-03-01",
                    "partner_id": cls.company_data["company"].partner_id.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 2.0,
                                "price_unit": 1500.0,
                                "tax_ids": [
                                    (6, 0, cls.company_data["default_tax_sale"].ids)
                                ],
                            },
                        )
                    ],
                },
                {
                    "move_type": "out_refund",
                    "invoice_date": fields.Date.from_string(
                        time.strftime("%Y-%m") + "-01"
                    ),
                    "date": fields.Date.from_string(time.strftime("%Y-%m") + "-01"),
                    "partner_id": cls.partner_a.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 3.0,
                                "price_unit": 1000.0,
                                "tax_ids": [
                                    (6, 0, cls.company_data["default_tax_sale"].ids)
                                ],
                            },
                        )
                    ],
                },
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.from_string(
                        time.strftime("%Y-%m") + "-01"
                    ),
                    "date": fields.Date.from_string(time.strftime("%Y-%m") + "-01"),
                    "partner_id": cls.partner_b.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product_b.id,
                                "quantity": 10.0,
                                "price_unit": 800.0,
                                "tax_ids": [
                                    (6, 0, cls.company_data["default_tax_purchase"].ids)
                                ],
                            },
                        )
                    ],
                },
            ]
        )
        invoices.action_post()

    def test_run_report(self):
        wizard = self.env["l10n.ro.journal.register.report"].create({})
        wizard.button_show()
