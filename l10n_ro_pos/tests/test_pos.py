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

        # A CUI of its own (see l10n_ro_account/tests/test_payment.py): the one
        # of NextERP Romania SRL belongs to the partner the enterprise demo
        # data ships.
        cls.ro_partner = cls.env["res.partner"].create(
            {
                "name": "RO Partner",
                "country_id": cls.env.ref("base.ro").id,
                "vat": "RO12345674",
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
        # ``company_data["default_warehouse"]`` comes from the valuation
        # reconciliation common, which CommonPosTest does not build on; the
        # warehouse of the user is what Odoo's own pos_stock tests take.
        warehouse = self.env.user._get_default_warehouse_id()
        stock_location = warehouse.lot_stock_id
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        receipt = self.env["stock.move"].create(
            {
                "product_id": self.product_a.id,
                "uom_id": self.product_a.uom_id.id,
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
        # Two units at 100: the totals and the payment have to say 200 as
        # well, because Odoo 20 refuses an order that is not fully paid.
        order_data = {
            "amount_paid": 200.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 200.0,
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
                        "amount": 200.0,
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

    def test_closing_entry_does_not_repost_the_goods_issue(self):
        """The closing entry must not book the goods issue a second time."""
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
        # Odoo 20 nu mai acumuleaza sume in buckets: pos_stock adauga direct
        # perechea cheltuiala/stoc pe nota de inchidere, cate una pe miscare.
        commands = session._prepare_session_closing_extra_line_commands(
            order, refund=False
        )
        accounts = self.product_a.product_tmpl_id._get_product_accounts()
        goods_issue_accounts = {
            accounts["expense"].id,
            accounts["stock_valuation"].id,
        }
        posted_by_the_move = order.picking_ids.move_ids.filtered("account_move_id")

        if session._l10n_ro_stock_move_posts_goods_issue():
            self.assertTrue(
                posted_by_the_move,
                "Miscarea de stoc trebuie sa-si posteze singura descarcarea",
            )
            self.assertFalse(
                [
                    command
                    for command in commands
                    if command[2].get("account_id") in goods_issue_accounts
                ],
                "Nota de inchidere nu trebuie sa mai contina descarcarea de "
                "gestiune: ea vine din miscarea de stoc",
            )
        else:
            # Fara l10n_ro_stock_account nimeni nu posteaza iesirea din
            # gestiune, deci nota de inchidere ramane singura sursa a ei.
            self.assertFalse(posted_by_the_move)

    def test_closing_an_uninvoiced_session_carries_no_stock(self):
        """Close a session on an order that was not invoiced.

        This is the path that can break: on an ordinary till sale ``pos_stock``
        appends an expense/stock pair for each stock move of the session, and
        without taking those off again the closing entry books the cost of the
        goods a second time - the Romanian stock move has already posted that
        discharge - or, worse, carries a valuation line whose counterpart was
        cleared and comes out unbalanced.
        """
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        order_data = {
            "amount_paid": 100.0,
            "amount_return": 0,
            "amount_tax": 0,
            "amount_total": 100.0,
            "date_order": "2024-01-01 10:00:00",
            "name": "Order 0002",
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
            "uuid": "0002",
            "to_invoice": False,
        }
        self.env["pos.order"].sync_from_ui([order_data])

        session.action_pos_session_closing_control()
        self.assertEqual(session.state, "closed")

        closing_accounts = session.move_id.line_ids.account_id
        accounts = self.product_a.product_tmpl_id.get_product_accounts()
        for key in ("stock_valuation", "stock_output", "expense"):
            account = accounts.get(key)
            if account:
                self.assertNotIn(
                    account,
                    closing_accounts,
                    f"Nota de inchidere contine o linie de {key}",
                )
        self.assertAlmostEqual(
            sum(session.move_id.line_ids.mapped("debit")),
            sum(session.move_id.line_ids.mapped("credit")),
            places=2,
            msg="Nota de inchidere nu este echilibrata",
        )
