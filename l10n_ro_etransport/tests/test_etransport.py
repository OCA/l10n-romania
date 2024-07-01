from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestETransport(TransactionCase):
    def setUp(self):
        super(TestETransport, self).setUp()

        country_ro = self.env["res.country"].search([("code", "=", "RO")])
        self.env.company.l10n_ro_accounting = True
        self.env.company.partner_id.write(
            {
                "name": "Test Company",
                "country_id": country_ro.id,
                "vat": "RO123456789",
                "state_id": self.env.ref("base.RO_BC").id,
                "street": "Test Street Company",
                "city": "Test City Company",
                "zip": "123456",
                "phone": "123456789",
            }
        )
        ResPartner = self.env["res.partner"].with_context(no_vat_validation=True)
        self.partner = ResPartner.create(
            {
                "name": "Test Partner",
                "country_id": country_ro.id,
                "state_id": self.env.ref("base.RO_IS").id,
                "vat": "RO123456781",
                "street": "Test Street Partner",
                "city": "Test City Partner",
                "zip": "123456",
                "phone": "123456789",
            }
        )
        self.partner.street = "Test Street Partner"
        if "street_name" in self.partner:
            self.partner.street_name = "Test Street Name Partner"

        self.partner_carrier = ResPartner.create(
            {
                "name": "Test Partner Carrier",
                "country_id": country_ro.id,
                "state_id": self.env.ref("base.RO_SV").id,
                "vat": "RO123456782",
                "street": "Test Street Carrier",
                "city": "Test City Carrier",
                "zip": "123456",
                "phone": "123456789",
            }
        )
        self.partner_carrier.street = "Test Street Carrier"
        if "street_name" in self.partner_carrier:
            self.partner_carrier.street_name = "Test Street Name Carrier"

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
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-transport")
        if not anaf_config:
            anaf_scope = {
                "scope": "e-transport",
                "state": "test",
                "anaf_sync_test_url": "https://api.anaf.ro/test/ETRANSPORT/ws/v1",
                "anaf_sync_production_url": "https://api.anaf.ro/prod/ETRANSPORT/ws/v1",
            }
            self.env["l10n.ro.account.anaf.sync"].create(
                {
                    "company_id": self.env.company.id,
                    "client_id": "123",
                    "client_secret": "123",
                    "access_token": "123",
                    "client_token_valability": date.today() + timedelta(days=10),
                    "anaf_scope_ids": [(0, 0, anaf_scope)],
                }
            )
            self.env.company._l10n_ro_get_anaf_sync(scope="e-transport")

    def test_e_transport(self):
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_type.id,
                "carrier_id": self.carrier.id,
                "l10n_ro_vehicle": "BC17DCH",
                "l10n_ro_e_transport_operation_type_id": self.env.ref(
                    "l10n_ro_etransport.operation_30"
                ).id,
                "l10n_ro_e_transport_scope_id": self.env.ref(
                    "l10n_ro_etransport.scope_101"
                ).id,
                "location_id": self.picking_type.default_location_src_id.id,
                "location_dest_id": self.picking_type.default_location_dest_id.id,
                "move_ids": [
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

        test_data_not_ok = {
            "Errors": [{"errorMessage": "UIT-ul nu poate fi identificat."}],
            "stare": "nok",
            "dateResponse": "202208021055",
            "ExecutionStatus": 1,
            "trace_id": "c78c23fa-a230-45d7-8fd6-e3bee8e13f41",
        }
        picking.with_context(test_data=test_data_not_ok).export_e_transport_button()
