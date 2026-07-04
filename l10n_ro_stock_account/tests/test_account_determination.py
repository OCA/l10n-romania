# Copyright (C) 2025 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.tests import tagged

from .common import TestStockCommon


@tagged("post_install", "-at_install")
class TestStockAccountDetermination(TestStockCommon):
    """Verificare determinare conturi contabile analitice pentru fiecare depozit"""

    # se vor defini doua depzoite cu conturi contabile diferite
    # 371 va deveni 371.1 si respectiv 371.2
    # 607 va deveni 607.1 si respectiv 607.2
    # 707 va deveni 707.1 si respectiv 707.2

    @classmethod
    def setUpAccounts(cls):
        res = super().setUpAccounts()

        cls.account_371_1 = cls.account_valuation.copy({"name": "371001"})
        cls.account_371_2 = cls.account_valuation.copy({"name": "371002"})
        cls.account_607_1 = cls.account_expense.copy({"name": "607001"})
        cls.account_607_2 = cls.account_expense.copy({"name": "607002"})
        cls.account_707_1 = cls.account_income.copy({"name": "707001"})
        cls.account_707_2 = cls.account_income.copy({"name": "707002"})

        # definire pozitie fiscale pentru depozitul 1

        cls.fiscal_position_1 = cls.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position 1",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_valuation.id,
                            "account_dest_id": cls.account_371_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_expense.id,
                            "account_dest_id": cls.account_607_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_income.id,
                            "account_dest_id": cls.account_707_1.id,
                        },
                    ),
                ],
            }
        )
        cls.fiscal_position_2 = cls.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position 2",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_valuation.id,
                            "account_dest_id": cls.account_371_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_expense.id,
                            "account_dest_id": cls.account_607_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_src_id": cls.account_income.id,
                            "account_dest_id": cls.account_707_2.id,
                        },
                    ),
                ],
            }
        )
        cls.stock_journal_1 = cls.env["account.journal"].create(
            {
                "name": "Stock Journal 1",
                "type": "general",
                "code": "STK1",
                "l10n_ro_fiscal_position_id": cls.fiscal_position_1.id,
            }
        )
        cls.stock_journal_2 = cls.env["account.journal"].create(
            {
                "name": "Stock Journal 2",
                "type": "general",
                "code": "STK2",
                "l10n_ro_fiscal_position_id": cls.fiscal_position_2.id,
            }
        )

        cls.warehouse_1 = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse 1",
                "code": "WH_D1",
                "company_id": cls.env.company.id,
                "l10n_ro_property_stock_journal_id": cls.stock_journal_1.id,
            }
        )

        cls.warehouse_2 = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse 2",
                "code": "WH_D2",
                "company_id": cls.env.company.id,
                "l10n_ro_property_stock_journal_id": cls.stock_journal_2.id,
            }
        )

        return res

    def test_account_determination(self):
        picking_type_in = self.warehouse_1.in_type_id
        self.create_po(picking_type_in=picking_type_in)
        self.check_stock_valuation(self.val_p1_i, self.val_p2_i, self.account_371_1)

    def test_account_determination_multiline_same_account(self):
        """A posting can impact a single stock account through several lines
        whose individual balances don't equal ``svl.value``, only their sum
        does (e.g. a landed cost split between capitalizing on remaining
        stock and expensing to 607 the part already sold, both legs hitting
        the SAME stock account). ``_compute_account`` must match on the
        account's aggregated balance, not bail out to the category's default
        account just because no single line matches on its own.
        """
        self.create_po()
        move = self.picking.move_ids.filtered(lambda m: m.product_id == self.product_1)

        target_account = self.account_valuation.copy({"name": "371999"})
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        account_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": target_account.id,
                            "product_id": self.product_1.id,
                            "credit": 60.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": target_account.id,
                            "product_id": self.product_1.id,
                            "credit": 40.0,
                        },
                    ),
                    (0, 0, {"account_id": self.account_expense.id, "debit": 100.0}),
                ],
            }
        )
        account_move.action_post()

        svl = self.env["stock.valuation.layer"].create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_1.id,
                "stock_move_id": move.id,
                "quantity": 0.0,
                "value": -100.0,
                "account_move_id": account_move.id,
            }
        )
        self.assertEqual(svl.l10n_ro_account_id, target_account)

    def test_account_determination_multiline_multiproduct_same_account(self):
        """A single journal entry can cover several products on the SAME
        stock account (e.g. one landed cost split across a whole shipment).
        ``_compute_account`` must restrict the per-account aggregation to
        this layer's own product — otherwise another product's lines on the
        same account get folded into the sum, the total no longer matches
        either product's individual ``value``, and both silently fall back
        to the category's default account.
        """
        self.create_po()
        move_1 = self.picking.move_ids.filtered(
            lambda m: m.product_id == self.product_1
        )
        move_2 = self.picking.move_ids.filtered(
            lambda m: m.product_id == self.product_2
        )

        target_account = self.account_valuation.copy({"name": "371998"})
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        account_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": target_account.id,
                            "product_id": self.product_1.id,
                            "credit": 100.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": target_account.id,
                            "product_id": self.product_2.id,
                            "credit": 25.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {"account_id": self.account_expense.id, "debit": 125.0},
                    ),
                ],
            }
        )
        account_move.action_post()

        svl_1 = self.env["stock.valuation.layer"].create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_1.id,
                "stock_move_id": move_1.id,
                "quantity": 0.0,
                "value": -100.0,
                "account_move_id": account_move.id,
            }
        )
        svl_2 = self.env["stock.valuation.layer"].create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_2.id,
                "stock_move_id": move_2.id,
                "quantity": 0.0,
                "value": -25.0,
                "account_move_id": account_move.id,
            }
        )
        self.assertEqual(svl_1.l10n_ro_account_id, target_account)
        self.assertEqual(svl_2.l10n_ro_account_id, target_account)
