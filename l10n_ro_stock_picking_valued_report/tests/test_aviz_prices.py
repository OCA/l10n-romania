# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


class AvizPricesCases:
    def _create_outgoing_picking(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.location.warehouse_id.out_type_id.id,
                "location_id": self.location.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )

    def test_outgoing_aviz_honours_the_company_setting(self):
        picking = self._create_outgoing_picking()
        self.assertEqual(picking.picking_type_id.code, "outgoing")

        self.env.company.l10n_ro_print_aviz_with_prices = True
        self.assertTrue(picking._l10n_ro_show_aviz_prices())
        self.env.company.l10n_ro_print_aviz_with_prices = False
        self.assertFalse(picking._l10n_ro_show_aviz_prices())

        report_view = self.env.ref(
            "l10n_ro_stock_picking_valued_report.report_delivery_document"
        )
        self.assertIn("_l10n_ro_show_aviz_prices()", report_view.arch)

    def test_reception_always_keeps_its_prices(self):
        self.env.company.l10n_ro_print_aviz_with_prices = False
        incoming_move = self._receive(10, 1.0, 1)
        picking = incoming_move.picking_id

        self.assertEqual(picking.picking_type_id.code, "incoming")
        self.assertTrue(picking._l10n_ro_show_aviz_prices())
