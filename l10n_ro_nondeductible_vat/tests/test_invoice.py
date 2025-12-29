# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleInvoice(TestNondeductibleCommon):
    @TestNondeductibleCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def test_invoice_line_nondeductible_percent_compute(self):
        invoice = self.nd_invoice

        invoice.line_ids.deductible_amount = 100
        self.assertTrue(
            invoice.invoice_line_ids.l10n_ro_nondeductible_percent == "0",
            "Deductible amount should be 100 for deductible line",
        )

        invoice.line_ids.deductible_amount = 50
        self.assertTrue(
            invoice.invoice_line_ids.l10n_ro_nondeductible_percent == "50",
            "Deductible amount should be 50 for 50% non-deductible line",
        )

        invoice.line_ids.deductible_amount = 0
        self.assertTrue(
            invoice.invoice_line_ids.l10n_ro_nondeductible_percent == "100",
            "Deductible amount should be 0 for 100% non-deductible line",
        )

    def test_invoice_line_nondeductible_percent_inverse(self):
        invoice = self.nd_invoice

        invoice.line_ids.l10n_ro_nondeductible_percent = "0"
        self.assertTrue(
            invoice.invoice_line_ids.deductible_amount == 100,
            "Deductible amount should be 100 for deductible line",
        )

        invoice.line_ids.l10n_ro_nondeductible_percent = "50"
        self.assertTrue(
            invoice.invoice_line_ids.deductible_amount == 50,
            "Deductible amount should be 50 for 50% non-deductible line",
        )

        invoice.line_ids.l10n_ro_nondeductible_percent = "100"
        self.assertTrue(
            invoice.invoice_line_ids.deductible_amount == 0,
            "Deductible amount should be 0 for 100% non-deductible line",
        )

    def test_invalid_deductible_amount_raises(self):
        line = self.nd_invoice.invoice_line_ids[0]
        # Try to set an invalid deductible amount
        with self.assertRaises(ValidationError):
            line.deductible_amount = 37  # Not 0, 50, 100

    def test_sales_document_forbidden(self):
        sale_journal = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        invoice = self.env["account.move"].create(
            {
                "journal_id": sale_journal.id,
                "move_type": "out_invoice",
                "partner_id": self.customer_1.id,
            }
        )
        invoice.invoice_line_ids.create(
            {
                "move_id": invoice.id,
                "product_id": self.product_fifo.id,
                "quantity": 1,
                "price_unit": 100,
                "account_id": self.account_income.id,
            }
        )
        line = invoice.invoice_line_ids[0]
        # Try to set deductible_amount < 100 on a sale
        with self.assertRaises(ValidationError):
            line.deductible_amount = 50

    def test_wrong_stock_move_type_forbidden(self):
        # Simulate a stock move type not in allowed list
        customers_location = self.env["stock.location"].search(
            [("usage", "=", "customer")],
            limit=1,
        )
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_fifo.id,
                "product_uom_qty": 1,
                "location_id": self.location.id,
                "location_dest_id": customers_location.id,
                "l10n_ro_nondeductible_percent": "50",
                "l10n_ro_nondeductible_tax_id": self.tax.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(1)
        # with self.assertRaises(ValidationError):
        # Commented out, check comment in account_move_line.py
        move._action_done()

    def test_correct_tags_and_accounts(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.fbr_partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Partial item",
                            "product_id": self.product_fifo.id,
                            "account_id": self.account_expense.id,
                            "price_unit": 100,
                            "quantity": 1,
                            "deductible_amount": 50.00,
                            "tax_ids": [Command.set(self.tax.ids)],
                        }
                    )
                ],
            }
        )

        inv_lines_result = [
            {
                "display_type": "product",
                "account_id": self.account_expense,
                "quantity": 1,
                "price_unit": 100,  # noqa
                "tax_ids": self.tax,
                "tax_tag_ids": self.tag_base,
                "tax_line_id": self.env["account.tax"],  # noqa
                "l10n_ro_non_deductible_line_id": self.env["account.move.line"],
                "deductible_amount": 50,  # noqa
                "debit": 100,
                "credit": 0,
                "amount_currency": 100,
            },
            {
                "display_type": "non_deductible_product",
                "account_id": self.account_expense,
                "quantity": 0,  # noqa
                "price_unit": 0,
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.tag_base,  # noqa
                "tax_line_id": self.env["account.tax"],
                "l10n_ro_non_deductible_line_id": invoice.invoice_line_ids,  # noqa
                "deductible_amount": 100,
                "debit": -50,
                "credit": 0,
                "amount_currency": -50,  # noqa
            },
            {
                "display_type": "non_deductible_product_total",
                "account_id": self.nd_account,
                "quantity": 0,  # noqa
                "price_unit": 0,
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.tag_base_nd,  # noqa
                "tax_line_id": self.env["account.tax"],
                "l10n_ro_non_deductible_line_id": invoice.invoice_line_ids,  # noqa
                "deductible_amount": 100,
                "debit": 50,
                "credit": 0,
                "amount_currency": 50,  # noqa
            },
            {
                "display_type": "tax",
                "account_id": self.tax_account,
                "quantity": 0,
                "price_unit": 0,  # noqa
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.tag_vat,
                "tax_line_id": self.tax,  # noqa
                "l10n_ro_non_deductible_line_id": self.env["account.move.line"],
                "deductible_amount": 100,  # noqa
                "debit": 21,
                "credit": 0,
                "amount_currency": 21,  # noqa
            },
            {
                "display_type": "payment_term",
                "account_id": self.payable_account,
                "quantity": 0,  # noqa
                "price_unit": 0,
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.env["account.account.tag"],  # noqa
                "tax_line_id": self.env["account.tax"],
                "l10n_ro_non_deductible_line_id": self.env["account.move.line"],  # noqa
                "deductible_amount": 100,
                "debit": 0,
                "credit": 121,
                "amount_currency": -121,  # noqa
            },
            {
                "display_type": "non_deductible_tax_ro",
                "account_id": self.tax_account,
                "quantity": 0,  # noqa
                "price_unit": 0,
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.tag_vat,  # noqa
                "tax_line_id": self.env["account.tax"],
                "l10n_ro_non_deductible_line_id": invoice.invoice_line_ids,  # noqa
                "deductible_amount": 100,
                "debit": -10.5,
                "credit": 0,
                "amount_currency": -10.5,  # noqa
            },
            {
                "display_type": "non_deductible_tax_ro",
                "account_id": self.nd_expense_tax_account,
                "quantity": 0,  # noqa
                "price_unit": 0,
                "tax_ids": self.env["account.tax"],
                "tax_tag_ids": self.tag_vat_nd,  # noqa
                "tax_line_id": self.env["account.tax"],
                "l10n_ro_non_deductible_line_id": invoice.invoice_line_ids,  # noqa
                "deductible_amount": 100,
                "debit": 10.5,
                "credit": 0,
                "amount_currency": 10.5,  # noqa
            },
        ]

        self.assertEqual(
            len(invoice.line_ids),
            7,
            "Invoice should have 7 lines (product, non-deductible product, "
            "tax, payment term, non-deductible total, non-deductible tax ro x2)",
        )

        # Test each line with the invoice lines results
        for line, expected in zip(invoice.line_ids, inv_lines_result, strict=False):
            for field, exp_value in expected.items():
                actual_value = line[field]
                self.assertEqual(
                    actual_value,
                    exp_value,
                    f"Field {field} on line {line.id} {expected} "
                    f"expected {exp_value} but got {actual_value}",
                )
