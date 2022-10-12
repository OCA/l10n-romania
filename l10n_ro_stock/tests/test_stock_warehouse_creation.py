# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestStockWarehouseCreation(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestStockWarehouseCreation, cls).setUpClass(
            chart_template_ref=ro_template_ref
        )
        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True

    def setUp(self):
        super(TestStockWarehouseCreation, self).setUp()
        self.warehouse_obj = self.env["stock.warehouse"]

    def test_warehouse_creation(self):
        warehouse = self.warehouse_obj.create(
            {
                "name": "Warehouse Romania",
                "code": "ROW",
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(warehouse.l10n_ro_wh_consume_loc_id)
        self.assertTrue(warehouse.l10n_ro_wh_usage_loc_id)
        self.assertTrue(warehouse.l10n_ro_consume_type_id)
        self.assertTrue(warehouse.l10n_ro_usage_type_id)

        wh_stock_loc = warehouse.lot_stock_id
        wh_consume_loc = warehouse.l10n_ro_wh_consume_loc_id
        wh_usage_loc = warehouse.l10n_ro_wh_usage_loc_id
        consume_type = warehouse.l10n_ro_consume_type_id
        usage_type = warehouse.l10n_ro_usage_type_id

        self.assertTrue(wh_consume_loc.usage, "consume")
        self.assertTrue(wh_usage_loc.usage, "usage_giving")

        self.assertTrue(consume_type.code, "internal")
        self.assertTrue(consume_type.default_location_src_id, wh_stock_loc)
        self.assertTrue(consume_type.default_location_dest_id, wh_consume_loc)

        self.assertTrue(usage_type.code, "internal")
        self.assertTrue(usage_type.default_location_src_id, wh_stock_loc)
        self.assertTrue(usage_type.default_location_dest_id, wh_usage_loc)

    def test_warehouse_rename(self):
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Romania", "code": "ROW"}
        )
        warehouse._update_name_and_code(new_name="Warehouse", new_code="WRO")
