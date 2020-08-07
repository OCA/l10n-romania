# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form, TransactionCase

from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon


@tagged("post_install", "-at_install")
class TestRoSalePurchaseWizard(TransactionCase):
    def test_wizard_defaults(self):
        today = fields.Date.today()
        date_to = today.replace(day=1) - timedelta(days=1)
        date_from = today.replace(day=1) - timedelta(days=date_to.day)
        sale_journal = self.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        wiz_select_sale_purchase = self.env["l10n.ro.account.report.journal"]

        for journal_type in ["sale", "purchase"]:
            wizard = wiz_select_sale_purchase.create({"journal_type": journal_type})
            self.assertEqual(wizard.company_id, self.env.ref("base.main_company"))
            self.assertEqual(wizard.date_from, date_from)
            self.assertEqual(wizard.date_to, date_to)
            self.assertNotEqual(wizard.print_report().get("data", False), False)


@tagged("post_install", "-at_install")
class TestRoSalePurchaseJournal(InvoiceTestCommon):
    # is creating another company with accounts .from Romania chart tempalte

    @classmethod
    def setup_company_data(cls, company_name="", **kwargs):
        """ taken from  odoo.addons.account.tests.account_test_savepoint
        Create a new company with Romania accounts
        The current user will get access to this company.

        :return: A dictionary will be returned containing all relevant accounting data for testing.
        """
        chart_template = cls.env.ref("l10n_ro.ro_chart_template")
        company = cls.env["res.company"].create(
            {
                "name": "Romania test company",
                "currency_id": cls.env.ref("base.RON").id,
                **kwargs,
            }
        )
        cls.env.user.company_ids |= company
        cls.env.user.company_id = company

        chart_template = cls.env["account.chart.template"].browse(chart_template.id)
        chart_template.try_loading()

        return {
            "company": company,
            "currency": company.currency_id,
            "default_account_revenue": cls.env["account.account"].search(
                [
                    ("company_id", "=", company.id),
                    (
                        "user_type_id",
                        "=",
                        cls.env.ref("account.data_account_type_revenue").id,
                    ),
                ],
                limit=1,
            ),
            "default_account_expense": cls.env["account.account"].search(
                [
                    ("company_id", "=", company.id),
                    (
                        "user_type_id",
                        "=",
                        cls.env.ref("account.data_account_type_expenses").id,
                    ),
                ],
                limit=1,
            ),
            "default_account_receivable": cls.env["account.account"].search(
                [
                    ("company_id", "=", company.id),
                    ("user_type_id.type", "=", "receivable"),
                ],
                limit=1,
            ),
            "default_account_payable": cls.env["account.account"].search(
                [
                    ("company_id", "=", company.id),
                    ("user_type_id.type", "=", "payable"),
                ],
                limit=1,
            ),
            "default_account_tax_sale": company.account_sale_tax_id.mapped(
                "invoice_repartition_line_ids.account_id"
            ),
            "default_account_tax_purchase": company.account_purchase_tax_id.mapped(
                "invoice_repartition_line_ids.account_id"
            ),
            "default_journal_misc": cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "general")], limit=1
            ),
            "default_journal_sale": cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
            ),
            "default_journal_purchase": cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "purchase")], limit=1
            ),
            "default_journal_bank": cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "bank")], limit=1
            ),
            "default_journal_cash": cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "cash")], limit=1
            ),
            "default_tax_sale": company.account_sale_tax_id,
            "default_tax_purchase": company.account_purchase_tax_id,
        }

    @classmethod
    def setUpClass(cls):
        super(TestRoSalePurchaseJournal, cls).setUpClass()

        # partner_a,& _b created in odoo.addons.account.tests.invoice_test_common
        cls.partner_c = cls.env["res.partner"].create(
            {
                "name": "partner_c",
                "property_payment_term_id": cls.pay_terms_a.id,
                "property_supplier_payment_term_id": cls.pay_terms_a.id,
                "property_account_receivable_id": cls.company_data[
                    "default_account_receivable"
                ].id,
                "property_account_payable_id": cls.company_data[
                    "default_account_payable"
                ].id,
                #'fiscal_position':,
                "company_id": False,
            }
        )

        cls.invoices = cls.env["account.move"].create(
            [
                {
                    "type": "out_invoice",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-01-01"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 100,
                                "tax_ids": [
                                    (6, 0, [cls.env.ref("l10n_ro.1_tvac_19").id])
                                ],
                            },
                        ),
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 200,
                                "tax_ids": [
                                    (6, 0, [cls.env.ref("l10n_ro.1_tvac_05").id])
                                ],
                            },
                        ),
                    ],
                },
                {
                    "type": "out_invoice",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-01-02"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 3,
                                "price_unit": 1000,
                            },
                        ),
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 3000,
                            },
                        ),
                    ],
                },
                {
                    "type": "out_receipt",
                    "invoice_date": fields.Date.from_string("2016-01-03"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 6000,
                            },
                        ),
                    ],
                },
                {
                    "type": "out_refund",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-01-04"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 1200,
                            },
                        ),
                    ],
                },
                {
                    "type": "in_invoice",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-02-01"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 60,
                            },
                        ),
                    ],
                },
                {
                    "type": "in_receipt",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-02-02"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 60,
                            },
                        ),
                    ],
                },
                {
                    "type": "in_refund",
                    "partner_id": cls.partner_a.id,
                    "invoice_date": fields.Date.from_string("2016-02-03"),
                    "currency_id": cls.env.ref("base.RON").id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product_a.id,
                                "quantity": 1,
                                "price_unit": 12,
                            },
                        ),
                    ],
                },
            ]
        )

    #         print invoices
    #         for inv in cls.invoices:
    #             print(f"invoice id={inv.id} date={inv.date} amount_untaxed={inv.amount_untaxed},amount_tax={inv.amount_tax} amount_total={inv.amount_total} ")

    def assertInvoiceReportValues(self, expected_values_list, journal_type="sale"):
        report_obj = self.env[
            "report.l10n_ro_account_report_journal.report_sale_purchase"
        ]
        self.env["account.move"].search(
            [("company_id", "=", self.env.user.company_id.id)]
        ).post()
        data = {
            "form": {
                "company_id": (self.env.user.company_id.id, "name"),
                "date_from": "2016-01-01",
                "date_to": "2021-01-01",
                "journal_type": journal_type,
                "show_warnings": True,
            }
        }

        report_result = report_obj._get_report_values([], data)

        expected_resulted_values = []
        for line in report_result["lines"]:
            ret = {}
            for key, value in line.items():
                if key in ["date", "partner", "total"]:
                    continue
                elif (type(value) is float) and value != 0:
                    ret[key] = value
            expected_resulted_values += [ret]

        self.assertEqual(expected_values_list, expected_resulted_values)

    def test_sale_report(self):
        self.assertInvoiceReportValues(
            [
                {
                    "+Baza TVA 19%": 100.0,
                    "+Baza TVA 5%": 200.0,
                    "+TVA 19% (TVA colectata)": 19.0,
                    "+TVA 5% (TVA colectata)": 10.0,
                    "total_base": 300.0,
                    "total_vat": 29.0,
                },
                {"no_tag_like_vat0": 6000},
                {"no_tag_like_vat0": 6000},
                {"no_tag_like_vat0": -1200},
            ],
            "sale",
        )

    def test_purchase_report(self):
        self.assertInvoiceReportValues(
            [
                {"no_tag_like_vat0": 60},
                {"no_tag_like_vat0": 60},
                {"no_tag_like_vat0": -12},
            ],
            "purchase",
        )
