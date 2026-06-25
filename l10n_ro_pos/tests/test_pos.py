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

    def test_sale_details_stock_columns(self):
        """Raportul Sale Details injecteaza cost unitar / valoare de stoc per produs."""
        report = self.env["report.point_of_sale.report_saledetails"]

        # Smoke: structura noua O19 + cheia de total, fara comenzi
        res = report.get_sale_details()
        self.assertIn("total_stock_amount", res)
        self.assertIsInstance(res.get("products"), list)

        # Seedam stoc (receptie 10 buc @ cost 60), ca iesirea sa fie valorizata
        # si sa nu cadem pe constraintul de stoc negativ.
        warehouse = self.company_data["default_warehouse"]
        stock_location = warehouse.lot_stock_id
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        receipt = self.env["stock.move"].create(
            {
                "product_id": self.product_a.id,
                "product_uom": self.product_a.uom_id.id,
                "product_uom_qty": 10.0,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
                "price_unit": 60.0,
            }
        )
        receipt._action_confirm()
        receipt._action_assign()
        receipt.move_line_ids.quantity = 10.0
        receipt.picked = True
        receipt._action_done()

        # Scenariu real: o comanda POS cu un produs cu cost
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        order_data = {
            "amount_paid": 100.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 100.0,
            "date_order": "2024-01-01 10:00:00",
            "name": "Order SD01",
            "partner_id": self.ro_partner.id,
            "session_id": session.id,
            "lines": [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "qty": 2,
                        "price_subtotal": 200.0,
                        "price_subtotal_incl": 200.0,
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
            "uuid": "SD01",
        }
        self.env["pos.order"].sync_from_ui([order_data])

        res = report.get_sale_details(session_ids=[session.id])
        # Gasim linia produsului in structura grupata pe categorii
        line = None
        for category in res.get("products", []):
            for product_line in category.get("products", []):
                if product_line.get("product_id") == self.product_a.id:
                    line = product_line
                    break
        self.assertIsNotNone(line, "Produsul vandut trebuie sa apara in raport")
        # Cheile de stoc trebuie injectate pe fiecare linie
        self.assertIn("stock_price", line)
        self.assertIn("stock_amount", line)
        # Cost mediu unitar din valorizarea miscarii de iesire (FIFO, receptie @ 60)
        self.assertGreater(line["stock_price"], 0.0)
        # stock_amount = cost unitar * cantitate vanduta
        self.assertAlmostEqual(
            line["stock_amount"], line["stock_price"] * line["quantity"], places=2
        )
        self.assertGreater(res["total_stock_amount"], 0.0)

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
        self.assertIn(
            "stock_valuation",
            data,
            "Trebuie să existe cheile pentru stoc în datele acumulate",
        )
        # Cheile de stoc trebuie să fie dict-uri goale, deoarece nu se generează
        # note contabile pentru stoc în l10n_ro_accounting (sunt generate în
        # mișcarea de stoc). În Odoo 19 aceste structuri sunt grupate pe cont și
        # consumate cu .items() la închiderea sesiunii — fiecare valoare ar fi
        # trebuit să fie un dict {amount, amount_converted}, deci golirea lor
        # previne generarea liniilor (și TypeError-ul de la iterare).
        #
        # "stock_valuation" trebuie golit explicit: e consumat separat de core în
        # _create_stock_valuation_lines, iar dacă rămâne populat generează o linie
        # de valorizare fără contrapartidă (stock_output e golit) => notă de
        # închidere dezechilibrată cu costul mărfii comenzilor nefacturate.
        for key in ["stock_expense", "stock_return", "stock_output", "stock_valuation"]:
            self.assertEqual(
                data[key],
                {},
                f"Cheia {key} ar trebui să fie goală deoarece nu se generează \
                note contabile pentru stoc",
            )
