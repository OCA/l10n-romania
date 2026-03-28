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

        cls.ro_partner = cls.env["res.partner"].create(
            {
                "name": "RO Partner",
                "country_id": cls.env.ref("base.ro").id,
                "vat": "RO39187746",
            }
        )
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

    def test_order_invoice_reference(self):
        """Test that the invoice created from a POS order has the correct reference."""
        # Creare sesiune POS
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
            "partner_id": self.ro_partner.id,
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

        # Validare comandă și creare factură
        order.action_pos_order_invoice()
        invoice = order.account_move
        self.assertEqual(len(invoice), 1, "Trebuie să se creeze o singură factură")
        self.assertEqual(
            invoice.ref,
            order.pos_reference,
            "Referința facturii trebuie să fie aceeași cu referința comenzii POS",
        )

    def test_session_accumulate_amounts(self):
        """Test that the amounts are accumulated correctly in the session."""
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        order_data = {
            "amount_paid": 100.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 100.0,
            "date_order": "2024-01-01 10:00:00",
            "name": "Order 0001",
            "partner_id": self.ro_partner.id,
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

        # Validare comandă și creare factură
        order.action_pos_order_invoice()
        data = session._accumulate_amounts({})
        self.assertIn(
            "stock_expense",
            data,
            "Trebuie să existe cheile pentru stoc în datele acumulate",
        )
        self.assertIn(
            "stock_return",
            data,
            "Trebuie să existe cheile pentru stoc în datele acumulate",
        )
        self.assertIn(
            "stock_output",
            data,
            "Trebuie să existe cheile pentru stoc în datele acumulate",
        )
        # All amounts related to stock should be 0.0 since no accounting entries
        # are generated for stock in l10n_ro_accounting:
        # amounts = {"amount": 0.0, "amount_converted": 0.0}
        for key in ["stock_expense", "stock_return", "stock_output"]:
            self.assertEqual(
                data[key]["amount"],
                0.0,
                f"Suma pentru {key} ar trebui să fie 0.0 deoarece nu se generează \
                note contabile pentru stoc",
            )
            self.assertEqual(
                data[key]["amount_converted"],
                0.0,
                f"Suma convertită pentru {key} ar trebui să fie 0.0 deoarece nu se \
                generează note contabile pentru stoc",
            )
