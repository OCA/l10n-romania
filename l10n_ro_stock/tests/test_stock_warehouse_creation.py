# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockWarehouseCreation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # These tests need a Romanian company, not the Romanian chart of
        # accounts that AccountTestInvoicingCommon rebuilds from scratch for
        # every post_install test class.
        cls.env.company.country_id = cls.env.ref("base.ro")
        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True
        cls.product_category = cls.env.ref("product.product_category_goods")
        cls.env.company._create_usage_location()
        cls.env.company._create_consume_location()

    def setUp(self):
        super().setUp()
        self.warehouse_obj = self.env["stock.warehouse"]

    def test_warehouse_creation(self):
        company = self.env.company
        warehouse = self.warehouse_obj.create(
            {
                "name": "Warehouse Romania",
                "code": "ROW",
                "company_id": self.env.company.id,
            }
        )

        self.assertTrue(warehouse.l10n_ro_consume_type_id)
        self.assertTrue(warehouse.l10n_ro_usage_type_id)

        wh_stock_loc = warehouse.lot_stock_id
        consume_loc = company.l10n_ro_consume_location_id
        usage_loc = company.l10n_ro_usage_location_id
        consume_type = warehouse.l10n_ro_consume_type_id
        usage_type = warehouse.l10n_ro_usage_type_id

        self.assertTrue(consume_loc.usage, "consume")
        self.assertTrue(usage_loc.usage, "usage_giving")

        self.assertTrue(consume_type.code, "internal")
        self.assertTrue(consume_type.default_location_src_id, wh_stock_loc)
        self.assertTrue(consume_type.default_location_dest_id, consume_loc)

        self.assertTrue(usage_type.code, "internal")
        self.assertTrue(usage_type.default_location_src_id, wh_stock_loc)
        self.assertTrue(usage_type.default_location_dest_id, usage_loc)

    def _return_type(self, warehouse, code):
        return self.env["stock.picking.type"].search(
            [("warehouse_id", "=", warehouse.id), ("sequence_code", "=", code)]
        )

    def test_return_types_created(self):
        """Fiecare operatie prin care marfa iese are drumul ei inapoi."""
        company = self.env.company
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Returns", "code": "RET", "company_id": company.id}
        )
        stock = warehouse.lot_stock_id
        vendors = warehouse._l10n_ro_location_by_usage("supplier")
        customers = warehouse._l10n_ro_location_by_usage("customer")

        expected = [
            # cod, felul miscarii, sursa, destinatia, operatia pe care o intoarce
            ("INR", "outgoing", stock, vendors, warehouse.in_type_id),
            ("OUTR", "incoming", customers, stock, warehouse.out_type_id),
            (
                "CONSR",
                "internal",
                company.l10n_ro_consume_location_id,
                stock,
                warehouse.l10n_ro_consume_type_id,
            ),
            (
                "USAGER",
                "internal",
                company.l10n_ro_usage_location_id,
                stock,
                warehouse.l10n_ro_usage_type_id,
            ),
        ]
        for code, direction, source, destination, forward in expected:
            backward = self._return_type(warehouse, code)
            self.assertEqual(len(backward), 1, f"{code} ar trebui sa existe, o data")
            self.assertEqual(backward.code, direction)
            self.assertEqual(backward.default_location_src_id, source)
            self.assertEqual(backward.default_location_dest_id, destination)
            # Imperecheate in amandoua sensurile, ca butonul de retur sa stie
            # pe ce drum sa trimita marfa inapoi.
            self.assertEqual(forward.return_picking_type_id, backward)
            self.assertEqual(backward.return_picking_type_id, forward)

    def test_purchase_return_goes_to_a_vendor_location(self):
        """Nota contabila se citeste de pe destinatie, deci ea decide tot.

        Catre o locatie de furnizor miscarea e retur de achizitie; catre una
        de client s-ar contabiliza ca o livrare, pe cheltuiala cu marfa
        vanduta.
        """
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Accounting", "code": "RACC"}
        )
        self.assertEqual(
            self._return_type(warehouse, "INR").default_location_dest_id.usage,
            "supplier",
        )

    def test_existing_return_type_is_reused(self):
        """Un tip care exista deja e completat, nu dublat."""
        company = self.env.company
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Saft", "code": "RSFT", "company_id": company.id}
        )
        self._return_type(warehouse, "INR").unlink()
        # Cum ajunge cand il face altcineva: fara locatii.
        existing = self.env["stock.picking.type"].create(
            {
                "name": "Return of purchase",
                "code": "outgoing",
                "sequence_code": "INR",
                "company_id": company.id,
                "warehouse_id": warehouse.id,
            }
        )
        warehouse.in_type_id.return_picking_type_id = existing

        warehouse._create_or_update_sequences_and_picking_types()

        self.assertEqual(
            self._return_type(warehouse, "INR"),
            existing,
            "tipul existent trebuie refolosit, nu dublat",
        )
        self.assertEqual(
            existing.default_location_dest_id,
            warehouse._l10n_ro_location_by_usage("supplier"),
            "tipul existent trebuie sa primeasca locatiile care ii lipseau",
        )

    def test_building_returns_twice_changes_nothing(self):
        """Rulata a doua oara, configurarea nu mai adauga nimic."""
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Twice", "code": "RTW"}
        )
        before = self.env["stock.picking.type"].search_count(
            [("warehouse_id", "=", warehouse.id)]
        )
        warehouse._create_or_update_sequences_and_picking_types()
        self.assertEqual(
            self.env["stock.picking.type"].search_count(
                [("warehouse_id", "=", warehouse.id)]
            ),
            before,
        )

    def test_warehouse_rename(self):
        warehouse = self.warehouse_obj.create(
            {"name": "Warehouse Romania", "code": "ROW"}
        )
        warehouse._update_name_and_code(new_name="Warehouse", new_code="WRO")

    def test_create_product(self):
        product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "is_storable": True,
                "categ_id": self.product_category.id,
                "l10n_ro_net_weight": 1.0,
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(product.product_tmpl_id.l10n_ro_net_weight)
        self.assertTrue(product.product_tmpl_id.l10n_ro_net_weight_uom_name)
        product.product_tmpl_id.l10n_ro_net_weight = 2.0
        self.assertEqual(product.l10n_ro_net_weight, 2.0)
