# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockLocation(TestROStockCommon):
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
