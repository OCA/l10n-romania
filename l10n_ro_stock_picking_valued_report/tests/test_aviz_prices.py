# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""The outgoing aviz prints with or without prices per a company setting."""

from odoo.tests import tagged

from .test_nir_report import TestNirReport


@tagged("post_install", "-at_install")
class TestAvizPrices(TestNirReport):
    def _deliver(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.location.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )

    def test_outgoing_aviz_honours_the_company_setting(self):
        """On an outgoing aviz the price/value columns follow the setting."""
        picking = self._deliver()
        self.assertEqual(picking.picking_type_id.code, "outgoing")
        self.env.company.l10n_ro_print_aviz_with_prices = True
        self.assertTrue(picking._l10n_ro_show_aviz_prices())
        self.assertTrue(picking._l10n_ro_show_valued_columns())
        self.env.company.l10n_ro_print_aviz_with_prices = False
        self.assertFalse(picking._l10n_ro_show_aviz_prices())
        self.assertFalse(picking._l10n_ro_show_valued_columns())

    def test_a_reception_always_keeps_its_prices(self):
        """The setting only touches the outgoing aviz; a NIR keeps its values
        even when outgoing avize are printed without prices."""
        self.env.company.l10n_ro_print_aviz_with_prices = False
        picking = self._receive(10, 1.0)
        self.assertEqual(picking.picking_type_id.code, "incoming")
        self.assertTrue(picking._l10n_ro_show_aviz_prices())
        self.assertTrue(picking._l10n_ro_show_valued_columns())
