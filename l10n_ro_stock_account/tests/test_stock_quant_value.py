# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon as RoTestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockQuantValue(RoTestStockCommon):
    def test_stock_quant_value(self):
        self.env.company.write({"l10n_ro_stock_account_svl_lot_allocation": False})
        product_serial_number = self.env["product.product"].create(
            {
                "name": "Test 1 Product",
                "type": "product",
                "list_price": 10.00,
                "standard_price": 5.00,
                "supplier_taxes_id": None,
                "tracking": "lot",
            }
        )
        product_serial_number.categ_id.property_cost_method = "fifo"
        stock_location = self.env["stock.location"].create(
            {
                "name": "Test Location",
                "usage": "internal",
                "company_id": self.env.company.id,
            }
        )
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        self.env.ref("stock.stock_location_customers")

        # Create stock moves for series 1, 2, 3, 4, and 5
        self.create_stock_move_in(
            "Series 1",
            "2023-12-01",
            1,
            10.0,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        self.create_stock_move_in(
            "Series 2",
            "2023-12-02",
            1,
            15.0,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        self.create_stock_move_in(
            "Series 3",
            "2023-12-03",
            1,
            20.0,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        self.create_stock_move_in(
            "Series 4",
            "2023-12-04",
            1,
            25.0,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        self.create_stock_move_in(
            "Series 5",
            "2023-12-05",
            10,
            5.0,
            product_serial_number,
            stock_location,
            supplier_location,
        )

        for series in ["Series 1", "Series 2", "Series 3", "Series 4", "Series 5"]:
            stock_quant_qty = self.get_stock_quant_qty(
                series, product_serial_number, stock_location
            )
            stock_valuation_layer_qty = self.get_stock_valuation_layer_qty(
                series, product_serial_number
            )
            self.assertEqual(
                stock_quant_qty,
                stock_valuation_layer_qty,
                f"Quantities do not match for {series}",
            )

        self.create_stock_move_out(
            "Series 3",
            "2023-12-06",
            1,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        svl3_out = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("quantity", "<", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 3"),
            ]
        )
        self.assertEqual(svl3_out.value, -10.0)
        svl3_remaining = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 3"),
            ]
        )
        self.assertEqual(svl3_remaining.remaining_value, 20.0)

        svl1 = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("l10n_ro_lot_ids.name", "=", "Series 1"),
            ]
        )
        self.assertEqual(svl1.remaining_qty, 0.0)
        self.assertEqual(svl1.remaining_value, 0.0)

        sq = self.env["stock.quant"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("location_id", "=", stock_location.id),
            ]
        )
        sq.sudo()._compute_value()

        sq1 = sq.filtered(lambda q: q.lot_id.name == "Series 1")
        self.assertEqual(sq1.quantity, 1.0)
        self.assertEqual(sq1.value, 20.0)

        sq2 = sq.filtered(lambda q: q.lot_id.name == "Series 2")
        self.assertEqual(sq2.quantity, 1.0)
        self.assertEqual(sq2.value, 15.0)

        sq3 = sq.filtered(lambda q: q.lot_id.name == "Series 3")
        self.assertEqual(sq3.quantity, 0.0)
        self.assertEqual(sq3.value, 0.0)

        sq4 = sq.filtered(lambda q: q.lot_id.name == "Series 4")
        self.assertEqual(sq4.quantity, 1.0)
        self.assertEqual(sq4.value, 25.0)

        sq5 = sq.filtered(lambda q: q.lot_id.name == "Series 5")
        self.assertEqual(sq5.quantity, 10.0)
        self.assertEqual(sq5.value, 50.0)

        self.create_stock_move_out(
            "Series 5",
            "2023-12-07",
            1,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        svl5_out = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("quantity", "<", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 5"),
            ]
        )
        self.assertEqual(svl5_out.value, -15.0)
        svl5_remaining = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 5"),
            ]
        )
        self.assertEqual(svl5_remaining.remaining_qty, 10.0)
        self.assertEqual(svl5_remaining.remaining_value, 50.0)
        svl2 = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 2"),
            ]
        )
        self.assertEqual(svl2.remaining_qty, 0.0)
        self.assertEqual(svl2.remaining_value, 0.0)

        sq = self.env["stock.quant"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("location_id", "=", stock_location.id),
            ]
        )
        sq.sudo()._compute_value()

        sq1 = sq.filtered(lambda q: q.lot_id.name == "Series 1")
        self.assertEqual(sq1.quantity, 1.0)
        self.assertEqual(sq1.value, 20.0)

        sq2 = sq.filtered(lambda q: q.lot_id.name == "Series 2")
        self.assertEqual(sq2.quantity, 1.0)
        self.assertEqual(sq2.value, 5.0)

        sq3 = sq.filtered(lambda q: q.lot_id.name == "Series 3")
        self.assertEqual(sq3.quantity, 0.0)
        self.assertEqual(sq3.value, 0.0)

        sq4 = sq.filtered(lambda q: q.lot_id.name == "Series 4")
        self.assertEqual(sq4.quantity, 1.0)
        self.assertEqual(sq4.value, 25.0)

        sq5 = sq.filtered(lambda q: q.lot_id.name == "Series 5")
        self.assertEqual(sq5.quantity, 9.0)
        self.assertEqual(sq5.value, 45.0)

        self.create_stock_move_out(
            "Series 5",
            "2023-12-08",
            1,
            product_serial_number,
            stock_location,
            supplier_location,
        )
        svl5_out = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("quantity", "<", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 5"),
            ],
            order="create_date desc",
            limit=1,
        )
        self.assertEqual(svl5_out.value, -20.0)
        svl5_remaining = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 5"),
            ]
        )
        self.assertEqual(svl5_remaining.remaining_qty, 10.0)
        self.assertEqual(svl5_remaining.remaining_value, 50.0)
        svl3 = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", "Series 3"),
            ]
        )
        self.assertEqual(svl3.remaining_qty, 0.0)
        self.assertEqual(svl3.remaining_value, 0.0)

        sq = self.env["stock.quant"].search(
            [
                ("product_id", "=", product_serial_number.id),
                ("location_id", "=", stock_location.id),
            ]
        )
        sq.sudo()._compute_value()
        sq1 = sq.filtered(lambda q: q.lot_id.name == "Series 1")
        self.assertEqual(sq1.quantity, 1.0)
        self.assertEqual(sq1.value, 5.0)

        sq2 = sq.filtered(lambda q: q.lot_id.name == "Series 2")
        self.assertEqual(sq2.quantity, 1.0)
        self.assertEqual(sq2.value, 5.0)

        sq3 = sq.filtered(lambda q: q.lot_id.name == "Series 3")
        self.assertEqual(sq3.quantity, 0.0)
        self.assertEqual(sq3.value, 0.0)

        sq4 = sq.filtered(lambda q: q.lot_id.name == "Series 4")
        self.assertEqual(sq4.quantity, 1.0)
        self.assertEqual(sq4.value, 25.0)

        sq5 = sq.filtered(lambda q: q.lot_id.name == "Series 5")
        self.assertEqual(sq5.quantity, 8.0)
        self.assertEqual(sq5.value, 40.0)

    def create_stock_move_in(
        self, series, date, qty, price_unit, product, stock_location, supplier_location
    ):
        lot = self.env["stock.lot"].create(
            {
                "name": series,
                "product_id": product.id,
            }
        )
        stock_move = self.env["stock.move"].create(
            {
                "name": "Test Stock Move",
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": product.uom_id.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
                "price_unit": price_unit,
                "date": date,
                "company_id": self.env.company.id,
                "origin": "Test Stock Move",
            }
        )
        stock_move._action_confirm()
        stock_move._action_assign()
        stock_move.move_line_ids.write({"lot_id": lot.id, "qty_done": qty})
        stock_move._action_done()

    def create_stock_move_out(
        self, series, date, qty, product, stock_location, supplier_location
    ):
        lot = self.env["stock.lot"].search(
            [("name", "=", series), ("product_id", "=", product.id)]
        )
        stock_move = self.env["stock.move"].create(
            {
                "name": "Test Stock Move Out",
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": product.uom_id.id,
                "location_id": stock_location.id,
                "location_dest_id": supplier_location.id,
                "date": date,
                "company_id": self.env.company.id,
                "origin": "Test Stock Move Out",
            }
        )
        stock_move._action_confirm()
        stock_move._action_assign()
        stock_move.move_line_ids.write({"lot_id": lot.id, "qty_done": qty})
        stock_move._action_done()
        self.env["stock.quant"]._quant_tasks()

    def get_stock_quant_qty(self, series, product_id, stock_location):
        stock_quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", product_id.id),
                ("location_id", "=", stock_location.id),
                ("lot_id.name", "=", series),
            ]
        )
        return [stock_quant.quantity, stock_quant.value]

    def get_stock_valuation_layer_qty(self, series, product_id):
        stock_valuation_layer = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", product_id.id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_lot_ids.name", "=", series),
            ]
        )
        return [
            stock_valuation_layer.remaining_qty,
            stock_valuation_layer.remaining_value,
        ]
