from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestStockMoveTracking(TestROStockCommon):
    @TestROStockCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()
        cls.StockMove = cls.env["stock.move"]
        cls.Tracking = cls.env["l10n.ro.stock.move.tracking"]
        src_move = cls.StockMove.create(
            {
                "product_id": cls.product_fifo.id,
                "product_uom_qty": 10,
                "product_uom": cls.product_fifo.uom_id.id,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.location1.id,
                "price_unit": 20,
                "value_manual": 200,
            }
        )

        src_move._action_confirm()
        src_move._action_assign()
        src_move.picked = True
        src_move._action_done()
        cls.src_move = src_move
        cls.dest_move = cls.StockMove.create(
            {
                "product_id": cls.product_fifo.id,
                "product_uom_qty": 5,
                "product_uom": cls.product_fifo.uom_id.id,
                "location_id": cls.location1.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
            }
        )
        cls.dest_move._action_confirm()
        cls.dest_move._action_assign()
        cls.dest_move.move_line_ids.quantity = 5.0
        cls.dest_move.picked = True
        cls.dest_move._action_done()

    def test_fifo_update_creates_tracking(self):
        new_dest_move = self.dest_move.copy()
        fifo_item = {
            "move_id": self.src_move.id,
            "quantity": 5,
        }
        # Simulate FIFO update
        new_dest_move._l10n_ro_update_fifo_move(fifo_item, new_dest_move)
        tracking = new_dest_move.l10n_ro_move_track_src_ids
        self.assertEqual(len(tracking), 1)
        self.assertEqual(tracking.src_move_id, self.src_move)
        self.assertEqual(tracking.quantity, 5)
        self.assertAlmostEqual(tracking.value, 100)

    def test_fifo_split_move_vals_tracking(self):
        fifo_item = {
            "move_id": self.src_move.id,
            "quantity": 3,
        }
        new_move_vals = {}
        fifo_quantity = 3
        self.dest_move._l10n_ro_update_fifo_split_move_vals(
            self.dest_move, new_move_vals, fifo_item, fifo_quantity
        )
        track_vals = new_move_vals.get("l10n_ro_move_track_src_ids", [])[0][2]
        self.assertEqual(track_vals["src_move_id"], self.src_move.id)
        self.assertEqual(track_vals["quantity"], 3)
        self.assertAlmostEqual(track_vals["value"], 60)
