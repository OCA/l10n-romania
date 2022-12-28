# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestMrpValuationStandardL10nRo(TestStockCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "ro_chart_template"
        super(TestMrpValuationStandardL10nRo, cls).setUpClass(
            chart_template_ref=ro_template_ref
        )

        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

        cls.fin_product = cls.env["product.product"].create(
            {
                "name": "Finished Product",
                "type": "product",
                "categ_id": cls.category.id,
                "invoice_policy": "delivery",
                "list_price": 0,
                "standard_price": 0,
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_id": cls.fin_product.id,
                "product_tmpl_id": cls.fin_product.product_tmpl_id.id,
                "product_uom_id": cls.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.product_1.id, "product_qty": 1})
                ],
            }
        )

    def test_fifo(self):
        self.fin_product.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "fifo"

        self.qty_po_p1 = 1
        self.price_p1 = 10
        self.create_po()

        self.qty_po_p1 = 1
        self.price_p1 = 20
        self.create_po()

        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()

        consume_moves = mo.move_raw_ids
        consume_svls = consume_moves.mapped("stock_valuation_layer_ids")
        self.assertEqual(len(consume_svls), 2)
        self.assertEqual(sum(consume_svls.mapped("value")), -30)

        self.assertEqual(self.product_1.value_svl, 0)
        self.assertEqual(self.product_1.quantity_svl, 0)

        self.assertEqual(self.fin_product.value_svl, 30)
        self.assertEqual(self.fin_product.quantity_svl, 2)

        self.assertEqual(self.fin_product.standard_price, 15)

    def test_avco(self):

        self.fin_product.product_tmpl_id.categ_id.property_cost_method = "average"
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "average"

        self.qty_po_p1 = 1
        self.price_p1 = 10
        self.create_po()

        self.qty_po_p1 = 1
        self.price_p1 = 20
        self.create_po()

        self.qty_po_p1 = 1
        self.price_p1 = 30
        self.create_po()

        mo = self._make_mo(self.bom, 3)
        self._produce(mo)
        mo.button_mark_done()

        consume_moves = mo.move_raw_ids
        consume_svls = consume_moves.mapped("stock_valuation_layer_ids")
        self.assertEqual(len(consume_svls), 3)
        self.assertEqual(sum(consume_svls.mapped("value")), -60)

        self.assertEqual(self.product_1.value_svl, 0)
        self.assertEqual(self.product_1.quantity_svl, 0)

        self.assertEqual(self.fin_product.value_svl, 60)
        self.assertEqual(self.fin_product.quantity_svl, 3)

        self.assertEqual(self.fin_product.standard_price, 20)
