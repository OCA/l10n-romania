from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged("post_install", "-at_install")
class TestReportPoSOrder(CommonPosTest):
    @classmethod
    @CommonPosTest.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True

        cls.env.user.group_ids += cls.env.ref("point_of_sale.group_pos_manager")

        # Configurare conturi și locații pentru testele RO
        cls.stock_journal = cls.env["account.journal"].create(
            {
                "name": "Stock Journal",
                "code": "STJT",
                "type": "general",
                "company_id": cls.env.company.id,
            }
        )
        cls.env.company.account_stock_journal_id = cls.stock_journal

        # Creare categorie de produs cu setări de localizare RO
        cls.category_marfa = cls.env["product.category"].create(
            {
                "name": "Marfa",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
            }
        )

        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Product A",
                "is_storable": True,
                "categ_id": cls.category_marfa.id,
                "lst_price": 100.0,
                "standard_price": 60.0,
                "available_in_pos": True,
            }
        )

        # Configurare locație cu cont de venituri specific (pentru testare pos_session)
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Venituri din vanzarea marfurilor",
                "code": "707",
                "account_type": "income",
            }
        )

    def test_pos_order_flow(self):
        """Testăm fluxul de bază: comandă, plată, facturare și închidere sesiune."""
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        # Creare comandă POS
        order_data = {
            "amount_paid": 100.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 100.0,
            "date_order": "2024-01-01 10:00:00",
            "name": "Order 0001",
            "partner_id": self.partner_adgu.id,
            "session_id": session.id,
            "lines": [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "qty": 1,
                        "price_subtotal": 100.0,
                        "price_subtotal_incl": 100.0,
                    }
                )
            ],
            "payment_ids": [
                Command.create(
                    {
                        "amount": 100.0,
                        "payment_method_id": self.cash_payment_method.id,
                    }
                )
            ],
            "uuid": "0001",
            "to_invoice": True,
        }

        result = self.env["pos.order"].sync_from_ui([order_data])
        order_id = result["pos.order"][0]["id"]
        order = self.env["pos.order"].browse(order_id)

        self.assertEqual(
            order.state,
            "done",
            "Comanda ar trebui să fie în starea 'done' după facturare în Odoo 19",
        )
        self.assertTrue(order.account_move, "Ar trebui să existe o factură")

        # Închidem sesiunea
        session.action_pos_session_closing_control()
        self.assertEqual(session.state, "closed", "Sesiunea ar trebui să fie închisă")

    def test_wizard_report(self):
        wizard = self.env["pos.details.wizard"].create({})
        wizard.generate_report()

    def test_report_saledetails(self):
        report_saledetails = self.env["report.point_of_sale.report_saledetails"]
        data = report_saledetails.get_sale_details()
        self.assertIn("products", data, "Raportul ar trebui să conțină produse")
        self.assertIn("payments", data, "Raportul ar trebui să conțină plăți")
        self.assertIn("taxes", data, "Raportul ar trebui să conțină taxe")

    def test_report_invoice(self):
        # Cream o comanda si o factura pentru a testa raportul cu date reale
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        order_data = {
            "amount_paid": 100.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 100.0,
            "date_order": "2024-01-01 10:00:00",
            "name": "Order 0002",
            "partner_id": self.partner_adgu.id,
            "session_id": session.id,
            "lines": [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "qty": 1,
                        "price_subtotal": 100.0,
                        "price_subtotal_incl": 100.0,
                    }
                )
            ],
            "payment_ids": [
                Command.create(
                    {
                        "amount": 100.0,
                        "payment_method_id": self.cash_payment_method.id,
                    }
                )
            ],
            "uuid": "0002",
            "to_invoice": True,
        }
        result = self.env["pos.order"].sync_from_ui([order_data])
        order_id = result["pos.order"][0]["id"]
        order = self.env["pos.order"].browse(order_id)
        # Flush to ensure record is available in DB for sudo() browse in report
        self.env.cr.flush()

        report_invoice = self.env["report.point_of_sale.report_invoice"].sudo()
        values = report_invoice._get_report_values([order.id], {})

        self.assertIn(
            "get_pickings", values, "Raportul ar trebui să conțină funcția get_pickings"
        )
        self.assertIn(
            "get_discount",
            values,
            "Raportul ar trebui să conțină valoarea get_discount",
        )
        self.assertTrue(
            callable(values["get_pickings"]), "get_pickings ar trebui să fie apelabil"
        )
