# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging

from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleInventory(TestNondeductibleCommon):
    @TestNondeductibleCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def _inventory_minus(self, percent="50", counted=9):
        """Remove `10 - counted` unit(s) (each valued 100) through an inventory
        adjustment with the given non-deductibility, mirroring what the user
        does in the on-hand list: edit the existing quant, set the counted
        quantity and the non-deductible tax, then apply. Returns the generated
        valuation account move."""
        quant = self.env["stock.quant"]._gather(self.product_fifo, self.location)
        quant = quant.with_context(inventory_mode=True)
        quant.write(
            {
                "l10n_ro_nondeductible_tax_id": self.tax.id,
                "l10n_ro_nondeductible_percent": percent,
                "inventory_quantity": counted,
            }
        )
        existing = self.env["stock.move"].search(
            [("product_id", "=", self.product_fifo.id)]
        )
        quant.action_apply_inventory()
        move = self.env["stock.move"].search(
            [("product_id", "=", self.product_fifo.id), ("id", "not in", existing.ids)],
            order="id desc",
            limit=1,
        )
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

    def test_inventory_minus_50_percent(self):
        """A 50% non-deductible inventory loss of goods valued 100 behaves like
        a consumption: no deductible VAT line, only the non-deductible base and
        VAT reversal."""
        account_move = self._inventory_minus("50")

        expected = sorted(
            [
                ("371000", "product", 0.0, 100.0, ()),
                ("607000", "product", 100.0, 0.0, ()),
                ("607000", "non_deductible_product", -50.0, 0.0, ("24 - TAX BASE",)),
                (
                    "607100",
                    "non_deductible_product_total",
                    50.0,
                    0.0,
                    ("24_2 - TAX BASE",),
                ),
                ("442600", "non_deductible_tax_ro", -10.5, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 10.5, 0.0, ("24_2 - VAT",)),
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

    def test_inventory_minus_100_percent(self):
        """A fully non-deductible inventory loss reverses the whole base/VAT."""
        account_move = self._inventory_minus("100")

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
