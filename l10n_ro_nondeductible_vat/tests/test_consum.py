# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleConsum(TestNondeductibleCommon):
    @TestNondeductibleCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def _consume(self, percent="50", qty=1):
        """Consume `qty` unit(s) (each valued 100) with the given
        non-deductibility, returning the generated valuation account move."""
        consume_location = self.env.company.l10n_ro_consume_location_id
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_fifo.id,
                "product_uom_qty": qty,
                "location_id": self.location.id,
                "location_dest_id": consume_location.id,
                "l10n_ro_nondeductible_percent": percent,
                "l10n_ro_nondeductible_tax_id": self.tax.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return move.account_move_id

    def _aml_signature(self, account_move):
        return sorted(
            (
                line.account_id.code,
                line.display_type,
                line.debit,
                line.credit,
                tuple(sorted(line.tax_tag_ids.mapped("name"))),
            )
            for line in account_move.line_ids
        )

    def test_consum_50_percent(self):
        """A 50% non-deductible consumption of goods valued 100 must not
        generate a deductible VAT line (nor an automatic balancing line):
        the VAT was already deducted on reception. Only the non-deductible
        reversal (base + VAT) is booked."""
        account_move = self._consume("50")

        expected = sorted(
            [
                # Base consumption 607 = 100 / 371 = 100, no tax grid on the
                # expense line (excluded from stock).
                ("371000", "product", 0.0, 100.0, ()),
                ("607000", "product", 100.0, 0.0, ()),
                # Non-deductible base reversal: 50% moved from the deductible
                # grid (24 - TAX BASE) to the non-deductible one.
                ("607000", "non_deductible_product", -50.0, 0.0, ("24 - TAX BASE",)),
                (
                    "607100",
                    "non_deductible_product_total",
                    50.0,
                    0.0,
                    ("24_2 - TAX BASE",),
                ),
                # Non-deductible VAT reversal: 50% of 21 = 10.5.
                ("442600", "non_deductible_tax_ro", -10.5, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 10.5, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(len(account_move.line_ids), 6)
        self.assertEqual(self._aml_signature(account_move), expected)
        # No deductible VAT line and no automatic balancing line.
        self.assertFalse(
            account_move.line_ids.filtered(lambda line: line.display_type == "tax")
        )
        self.assertEqual(
            sum(account_move.line_ids.mapped("debit")),
            sum(account_move.line_ids.mapped("credit")),
        )

    def test_consum_100_percent(self):
        """A fully non-deductible consumption reverses the whole base and VAT."""
        account_move = self._consume("100")

        expected = sorted(
            [
                ("371000", "product", 0.0, 100.0, ()),
                ("607000", "product", 100.0, 0.0, ()),
                ("607000", "non_deductible_product", -100.0, 0.0, ("24 - TAX BASE",)),
                (
                    "607100",
                    "non_deductible_product_total",
                    100.0,
                    0.0,
                    ("24_2 - TAX BASE",),
                ),
                ("442600", "non_deductible_tax_ro", -21.0, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 21.0, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(len(account_move.line_ids), 6)
        self.assertEqual(self._aml_signature(account_move), expected)
        self.assertFalse(
            account_move.line_ids.filtered(lambda line: line.display_type == "tax")
        )
        self.assertEqual(
            sum(account_move.line_ids.mapped("debit")),
            sum(account_move.line_ids.mapped("credit")),
        )
