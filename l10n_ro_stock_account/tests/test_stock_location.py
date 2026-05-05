# odoo-addons/l10n-romania-oca/l10n_ro_stock_account/tests/test_stock_location.py

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockLocation(TestStockCommon):
    def test_propagate_account_child_locations(self):
        """Test propagate_account with child stock locations"""

        # Create a parent location
        parent_location = self.env["stock.location"].create(
            {
                "name": "Parent Location",
                "l10n_ro_property_account_income_location_id": self.account_income.id,
                "l10n_ro_property_account_expense_location_id": self.account_expense.id,
                "l10n_ro_property_stock_valuation_account_id": self.account_valuation.id,  # noqa E501
            }
        )

        # Create child locations
        child_location_1 = self.env["stock.location"].create(
            {"name": "Child Location 1", "location_id": parent_location.id}
        )

        child_location_2 = self.env["stock.location"].create(
            {"name": "Child Location 2", "location_id": parent_location.id}
        )

        # Call the method on parent
        parent_location.propagate_account()

        # Assert values propagated to children
        self.assertEqual(
            child_location_1.l10n_ro_property_account_income_location_id.id,
            self.account_income.id,
        )
        self.assertEqual(
            child_location_1.l10n_ro_property_account_expense_location_id.id,
            self.account_expense.id,
        )
        self.assertEqual(
            child_location_1.l10n_ro_property_stock_valuation_account_id.id,
            self.account_valuation.id,
        )

        self.assertEqual(
            child_location_2.l10n_ro_property_account_income_location_id.id,
            self.account_income.id,
        )
        self.assertEqual(
            child_location_2.l10n_ro_property_account_expense_location_id.id,
            self.account_expense.id,
        )
        self.assertEqual(
            child_location_2.l10n_ro_property_stock_valuation_account_id.id,
            self.account_valuation.id,
        )

    def test_internal_transit_with_transfer_account(self):
        """Test transfer intre doua depozite prin tranzit cu cont de transfer.

        Scenariul:
        - Se configureaza l10n_ro_property_stock_transfer_account_id pe companie
        - Se face un transfer: depozit_sursa -> tranzit
          (internal_transit_in SVL = iesire din gestiune)
        - Se face un transfer: tranzit -> depozit_destinatie
          (internal_transit_out SVL = intrare in gestiune)
        - Se verifica ca notele contabile sunt corecte:
          internal_transit_in (depozit->tranzit):
            gestiunea_sursa (credit) -> cont_transfer (debit)
          internal_transit_out (tranzit->depozit):
            cont_transfer (credit) -> gestiunea_destinatie (debit)
        """
        company = self.env.company
        # Asiguram ca avem cont de transfer configurat
        self.assertTrue(
            self.account_stock_transfer,
            "Contul de transfer "
            "(l10n_ro_property_stock_transfer_account_id) nu este configurat",
        )
        company.l10n_ro_property_stock_transfer_account_id = self.account_stock_transfer

        # Setam stoc initial in depozitul sursa
        self.set_stock(self.product_mp, 10, location=self.location_warehouse)

        # Transfer din depozit sursa -> tranzit
        # (genereaza SVL internal_transit_in = iesire din gestiune)
        self.transfer(
            self.location_warehouse,
            self.location_transit,
            product=self.product_mp,
        )
        picking_out = self.picking

        # Verificam ca s-a generat SVL de tip internal_transit_in
        svl_out = self.env["stock.valuation.layer"].search(
            [
                ("stock_move_id", "in", picking_out.move_ids.ids),
                ("l10n_ro_valued_type", "=", "internal_transit_in"),
            ]
        )
        self.assertTrue(
            svl_out,
            "Nu s-a generat SVL de tip internal_transit_in (depozit->tranzit)",
        )

        # Verificam nota contabila pentru internal_transit_in (depozit->tranzit):
        # gestiunea sursa (credit) -> cont_transfer (debit)
        for svl in svl_out:
            am_lines = self.env["account.move.line"].search(
                [
                    ("stock_valuation_layer_ids", "in", svl.id),
                    ("parent_state", "=", "posted"),
                ]
            )
            if am_lines:
                debit_accounts = am_lines.filtered(lambda ln: ln.debit > 0).mapped(
                    "account_id"
                )
                credit_accounts = am_lines.filtered(lambda ln: ln.credit > 0).mapped(
                    "account_id"
                )
                self.assertIn(
                    self.account_stock_transfer,
                    debit_accounts,
                    "Contul de transfer trebuie sa fie pe debit" " in nota transit_out",
                )
                self.assertIn(
                    self.account_valuation,
                    credit_accounts,
                    "Contul de gestiune sursa trebuie sa fie pe credit"
                    " in nota transit_out",
                )

        # Transfer din tranzit -> depozit destinatie
        # (genereaza SVL internal_transit_out = intrare in gestiune)
        self.transfer(
            self.location_transit,
            self.location_warehouse_other,
            product=self.product_mp,
        )
        picking_in = self.picking

        # Verificam ca s-a generat SVL de tip internal_transit_out
        svl_in = self.env["stock.valuation.layer"].search(
            [
                ("stock_move_id", "in", picking_in.move_ids.ids),
                ("l10n_ro_valued_type", "=", "internal_transit_out"),
            ]
        )
        self.assertTrue(
            svl_in,
            "Nu s-a generat SVL de tip internal_transit_out (tranzit->depozit)",
        )

        # Verificam nota contabila pentru internal_transit_out (tranzit->depozit):
        # cont_transfer (credit) -> gestiunea destinatie (debit)
        for svl in svl_in:
            am_lines = self.env["account.move.line"].search(
                [
                    ("stock_valuation_layer_ids", "in", svl.id),
                    ("parent_state", "=", "posted"),
                ]
            )
            if am_lines:
                debit_accounts = am_lines.filtered(lambda ln: ln.debit > 0).mapped(
                    "account_id"
                )
                credit_accounts = am_lines.filtered(lambda ln: ln.credit > 0).mapped(
                    "account_id"
                )
                self.assertIn(
                    self.account_valuation,
                    debit_accounts,
                    "Contul de gestiune destinatie trebuie sa fie pe debit"
                    " in nota transit_in",
                )
                self.assertIn(
                    self.account_stock_transfer,
                    credit_accounts,
                    "Contul de transfer trebuie sa fie pe credit" " in nota transit_in",
                )
