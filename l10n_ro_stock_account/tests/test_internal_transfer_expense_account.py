# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestInternalTransferExpenseAccount(TestROStockCommon):
    """The incoming leg of an internal transfer takes the goods into the
    destination warehouse, so it must debit that warehouse's stock valuation
    account - never an expense account.

    `location1` (Test Warehouse 2) is the source that matters here: it carries
    both its own valuation account (371001) and its own expense account
    (607001). For an internal transfer the location accounts are always read
    from the source location, the source being internal, so the destination
    account resolved for `internal_transfer` used to be overwritten by that
    607001 - the value left the source warehouse as a cost and the destination
    warehouse never received it.

    The already existing transfer coverage never reproduced this: it either
    transfers *into* `location1` (a source without an expense account of its
    own) or between two sub-locations sharing the product's account.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_valuation_wh2 = (
            cls.location1.l10n_ro_property_stock_valuation_account_id
        )
        cls.account_expense_wh2 = (
            cls.location1.l10n_ro_property_account_expense_location_id
        )
        cls.account_transfer = (
            cls.env.company.l10n_ro_property_stock_transfer_account_id
        )
        # A sub-location of warehouse 2 inheriting both of its accounts, so a
        # transfer staying inside that warehouse has a source location with an
        # expense account and one single valuation account at both ends.
        cls.location1_sub = cls.env["stock.location"].create(
            {
                "name": "TW2 Sub Location",
                "usage": "internal",
                "location_id": cls.location1.id,
            }
        )
        cls.location1.propagate_account()

    def _receive(self, product, location, qty, price):
        self.test_case(
            {
                "steps": [
                    {
                        "type": "purchase",
                        "currency_id": self.env.company.currency_id,
                        "partner_id": self.supplier_1,
                        "product_id": product,
                        "location": location,
                        "step": 1,
                        "qty": qty,
                        "stock_qty": qty,
                        "inv_qty": qty,
                        "price": price,
                        "inv_price": price,
                    }
                ]
            }
        )

    def _transfer(self, product, location_src, location_dest, qty):
        """Validate a direct transfer and return every done transfer move.

        A FIFO product valued per location is split into one move per price
        layer consumed, so the transfer is not necessarily a single move.
        """
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return self.env["stock.move"].search(
            [
                ("product_id", "=", product.id),
                ("l10n_ro_move_type", "=", "internal_transfer"),
                ("state", "=", "done"),
            ]
        )

    def _balance(self, account):
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("company_id", "=", self.env.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        return sum(lines.mapped("balance"))

    def _check_transfer_entry(self, moves, expected_value, destination_account):
        self.assertTrue(moves)
        self.assertEqual(set(moves.mapped("l10n_ro_move_type")), {"internal_transfer"})
        self.assertAlmostEqual(sum(moves.mapped("value")), expected_value)

        lines = moves.account_move_id.line_ids
        self.assertTrue(lines, "the transfer posted no accounting entry at all")

        def balance(account):
            return sum(
                lines.filtered(lambda line: line.account_id == account).mapped(
                    "balance"
                )
            )

        # The goods left warehouse 2 and were taken into the destination
        # warehouse; the transfer account is only a pivot and nets to zero.
        self.assertAlmostEqual(balance(self.account_valuation_wh2), -expected_value)
        self.assertAlmostEqual(balance(destination_account), expected_value)
        self.assertAlmostEqual(balance(self.account_transfer), 0.0)
        # Nothing was expensed: without the fix the incoming leg debited the
        # source location's expense account instead of the destination.
        self.assertFalse(
            lines.filtered(lambda line: line.account_id == self.account_expense_wh2),
            "an internal transfer must not touch an expense account",
        )

    def test_avg_transfer_out_of_a_warehouse_with_its_own_accounts(self):
        self._receive(self.product_avg, self.location1, 10.0, 100.0)
        expense_before = self._balance(self.account_expense_wh2)

        moves = self._transfer(self.product_avg, self.location1, self.location, 10.0)

        self._check_transfer_entry(
            moves,
            1000.0,
            self.product_avg.categ_id.property_stock_valuation_account_id,
        )
        self.assertAlmostEqual(self._balance(self.account_expense_wh2), expense_before)

    def test_fifo_transfer_out_of_a_warehouse_with_its_own_accounts(self):
        """Same defect on FIFO, where the transfer is split per price layer."""
        self._receive(self.product_fifo, self.location1, 4.0, 100.0)
        self._receive(self.product_fifo, self.location1, 6.0, 150.0)
        expense_before = self._balance(self.account_expense_wh2)

        moves = self._transfer(self.product_fifo, self.location1, self.location, 10.0)

        # 4 x 100 + 6 x 150, whether it comes as one move or as one move per
        # layer consumed.
        self._check_transfer_entry(
            moves,
            1300.0,
            self.product_fifo.categ_id.property_stock_valuation_account_id,
        )
        self.assertAlmostEqual(self._balance(self.account_expense_wh2), expense_before)

    def test_transfer_inside_one_warehouse_posts_nothing(self):
        """One valuation account at both ends: no entry is due.

        The override also defeated the guard that suppresses the entry in that
        case, so such a transfer used to book the same spurious expense.
        """
        for product in (self.product_avg, self.product_fifo):
            with self.subTest(product=product.name):
                self._receive(product, self.location1, 10.0, 100.0)
                valuation_before = self._balance(self.account_valuation_wh2)
                expense_before = self._balance(self.account_expense_wh2)

                moves = self._transfer(
                    product, self.location1, self.location1_sub, 10.0
                )

                self.assertTrue(moves)
                self.assertEqual(
                    set(moves.mapped("l10n_ro_move_type")), {"internal_transfer"}
                )
                self.assertFalse(
                    moves.account_move_id,
                    "a transfer inside one valuation account posts nothing",
                )
                self.assertAlmostEqual(
                    self._balance(self.account_valuation_wh2), valuation_before
                )
                self.assertAlmostEqual(
                    self._balance(self.account_expense_wh2), expense_before
                )

    def test_transfer_of_a_category_without_location_accounts_posts_nothing(self):
        """A category not asking for the location accounts must not expense.

        Without ``l10n_ro_stock_account_change`` the location accounts are
        ignored altogether, so both ends of the transfer are the product's own
        valuation account and no entry is due - not the product's expense
        account, which is what the ``expense`` key holds when nothing
        overrides it.
        """
        category = self.env["product.category"].create(
            {
                "name": "Test category without location accounts",
                "property_valuation": "real_time",
                "property_cost_method": "average",
                "property_stock_valuation_account_id": (
                    self.env.company.account_stock_valuation_id.id
                ),
                "l10n_ro_stock_account_change": False,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Product Without Location Accounts",
                "is_storable": True,
                "purchase_method": "receive",
                "invoice_policy": "delivery",
                "categ_id": category.id,
            }
        )
        self._receive(product, self.location1, 10.0, 100.0)

        accounts = product.product_tmpl_id.get_product_accounts()
        expense_account = accounts["expense"]
        valuation_account = accounts["stock_valuation"]
        self.assertTrue(expense_account)
        self.assertNotEqual(expense_account, valuation_account)
        balances_before = {
            account: self._balance(account)
            for account in (
                expense_account,
                valuation_account,
                self.account_valuation_wh2,
                self.account_expense_wh2,
            )
        }

        moves = self._transfer(product, self.location1, self.location, 6.0)

        self.assertTrue(moves)
        self.assertEqual(set(moves.mapped("l10n_ro_move_type")), {"internal_transfer"})
        self.assertFalse(
            moves.account_move_id,
            "a transfer of a category without location accounts posts nothing",
        )
        for account, balance in balances_before.items():
            self.assertAlmostEqual(
                self._balance(account),
                balance,
                msg=f"account {account.code} was touched by the transfer",
            )

    def test_picking_journal_items_lists_the_extra_entries(self):
        """The Journal Items button must list the extra entries as well.

        A usage giving posts two entries: the valuation one on
        `account_move_id` and the off-balance one (8035) in
        `l10n_ro_extra_account_move_ids`. The button used to list only the
        first, so the rest of what the transfer posted was unreachable from
        the picking.
        """
        self._receive(self.product_avg, self.location1, 10.0, 100.0)
        picking = self.create_stock_picking(
            "usage_giving",
            {
                "type": "usage_giving",
                "currency_id": self.env.company.currency_id,
                "location": self.location1,
                "product_id": self.product_avg,
                "step": 1,
                "qty": 4.0,
                "stock_qty": 4.0,
                "index": 1,
            },
        )
        moves = picking.move_ids
        self.assertEqual(set(moves.mapped("l10n_ro_move_type")), {"usage_giving"})

        usage_account = self.env.company.l10n_ro_property_stock_usage_giving_account_id
        valuation_lines = moves.account_move_id.line_ids
        extra_lines = moves.l10n_ro_extra_account_move_ids.line_ids
        self.assertTrue(valuation_lines)
        self.assertTrue(
            extra_lines, "the off-balance entry of the usage giving is missing"
        )
        # The off-balance account is only on the extra entry, so it is the
        # proof of what the button was hiding.
        self.assertFalse(
            valuation_lines.filtered(lambda line: line.account_id == usage_account)
        )
        self.assertTrue(
            extra_lines.filtered(lambda line: line.account_id == usage_account)
        )

        action = picking.action_l10n_ro_view_account_moves()
        self.assertEqual(action.get("res_model"), "account.move.line")
        listed = set(action["domain"][0][2])
        self.assertTrue(set(valuation_lines.ids) <= listed)
        self.assertTrue(set(extra_lines.ids) <= listed)
