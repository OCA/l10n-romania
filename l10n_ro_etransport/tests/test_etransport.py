from odoo.tests.common import TransactionCase


class TestETransport(TransactionCase):
    def setUp(self):
        super(TestETransport, self).setUp()

        country_ro = self.env["res.country"].search([("code", "=", "RO")])

        self.env.company.partner_id.write(
            {
                "name": "Test Company",
                "country_id": country_ro.id,
                "vat": "RO123456789",
                "state_id": self.env.ref("base.RO_BC").id,
                "street": "Test Street",
                "city": "Test City",
                "zip": "123456",
                "phone": "123456789",
            }
        )

        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "country_id": country_ro.id,
                "state_id": self.env.ref("base.RO_IS").id,
                "vat": "RO123456781",
                "street": "Test Street",
                "city": "Test City",
                "zip": "123456",
                "phone": "123456789",
            }
        )

        self.partner_carrier = self.env["res.partner"].create(
            {
                "name": "Test Partner Carrier",
                "country_id": country_ro.id,
                "state_id": self.env.ref("base.RO_SV").id,
                "vat": "RO123456782",
                "street": "Test Street",
                "city": "Test City",
                "zip": "123456",
                "phone": "123456789",
            }
        )

        self.product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "default_code": "code1",
                "list_price": 100,
                "standard_price": 50,
                "weight": 5,
            }
        )

        self.product_delivery = self.env["product.product"].create(
            {
                "name": "Test Product Delivery",
                "type": "service",
                "default_code": "code2",
                "list_price": 100,
                "standard_price": 50,
                "weight": 5,
            }
        )

        self.carrier = self.env["delivery.carrier"].create(
            {
                "name": "Test Carrier",
                "delivery_type": "fixed",
                "fixed_price": 10,
                "product_id": self.product_delivery.id,
                "l10n_ro_e_partner_id": self.partner_carrier.id,
            }
        )
        self.picking_type = self.env["stock.picking.type"].create(
            {
                "name": "Test Picking Type",
                "code": "outgoing",
                "warehouse_id": self.env.ref("stock.warehouse0").id,
                "sequence_code": "TEST",
                "default_location_src_id": self.env.ref(
                    "stock.stock_location_stock"
                ).id,
                "default_location_dest_id": self.env.ref(
                    "stock.stock_location_customers"
                ).id,
            }
        )
        anaf_config = self.env.company.l10n_ro_account_anaf_sync_id
        if not anaf_config:
            anaf_config = self.env["l10n.ro.account.anaf.sync"].create(
                {
                    "company_id": self.env.company.id,
                    "client_id": "123",
                    "client_secret": "123",
                }
            )
            self.env.company.l10n_ro_account_anaf_sync_id = anaf_config

    def test_e_transport(self):
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type.id,
                "carrier_id": self.carrier.id,
                "l10n_ro_vehicle": "BC17DCH",
                "l10n_ro_e_transport_tip_operatie": "30",
                "l10n_ro_e_transport_scop": "101",
                "location_id": self.picking_type.default_location_src_id.id,
                "location_dest_id": self.picking_type.default_location_dest_id.id,
                "move_lines": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.picking_type.default_location_src_id.id,
                            "location_dest_id": self.picking_type.default_location_dest_id.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.button_validate()
        test_data = {
            "dateResponse": "202203071008",
            "ExecutionStatus": 0,
            "index_incarcare": 1234,
            "trace_id": "cd5d99d0-2f52-4072-9ed1-4004931ccc1b",
        }
        picking.with_context(test_data=test_data).export_e_transport_button()
