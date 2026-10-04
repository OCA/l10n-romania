# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import ast
import logging

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPickingValued(TestROStockCommon):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False

        cls.eur.rate_ids.create(
            {
                "name": fields.Date.today(),
                "rate": 5.0,
                "company_id": cls.env.company.id,
                "currency_id": cls.ron.id,
            }
        )

    def run_test_step(self, step):
        res = super().run_test_step(step)
        if step.get("checks_values"):
            if isinstance(step.get("checks_values"), dict):
                checks = step.get("checks_values")
            else:
                checks = ast.literal_eval(step["checks_values"])
            if checks:
                self.run_check_values(checks)
        return res

    def run_check_values(self, checks):
        if "picking" in checks:
            self.check_picking_values(checks["picking"])
        if "stock_move_lines" in checks:
            self.check_stock_move_lines_values(checks["stock_move_lines"])

    def check_picking_values(self, checks):
        for picking_ref, expected_values in checks.items():
            picking = getattr(self, picking_ref)
            for field_name, expected_value in expected_values.items():
                actual_value = getattr(picking, field_name)
                if self.log_checks:
                    _logger.info(
                        "Checking picking %s field %s: expected %s, got %s",
                        picking_ref,
                        field_name,
                        expected_value,
                        actual_value,
                    )
                self.assertEqual(
                    actual_value,
                    expected_value,
                    f"Picking {picking_ref} field {field_name}"
                    f" expected {expected_value}, got {actual_value}",
                )

    def check_stock_move_lines_values(self, checks):
        for picking_ref, expected_values in checks.items():
            picking = getattr(self, picking_ref)
            move_line = picking.move_line_ids
            agg_lines = move_line._get_aggregated_product_quantities()
            self.assertEqual(len(agg_lines.keys()), 1)
            line_key = self._get_agg_lines_key(move_line)
            self.assertTrue(agg_lines[line_key])
            for field_name, expected_value in expected_values.items():
                actual_value = agg_lines[line_key][field_name]
                if self.log_checks:
                    _logger.info(
                        "Checking Stock Move Line %s field %s: expected %s, got %s",
                        line_key,
                        field_name,
                        expected_value,
                        actual_value,
                    )
                self.assertEqual(
                    actual_value,
                    expected_value,
                    f"Stock Move Line {line_key} field {field_name} "
                    f"expected {expected_value}, got {actual_value}",
                )

    def _get_agg_lines_key(self, move_line):
        agg_properties = move_line._get_aggregated_properties(move_line=move_line)
        line_key = agg_properties["line_key"]
        return line_key
