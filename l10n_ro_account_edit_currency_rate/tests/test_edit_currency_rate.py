# Copyright 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestEditCurrencyRate(AccountTestInvoicingCommon):
    """
    Tests for l10n_ro_account_edit_currency_rate.

    Scenario:
      - Romanian company (country_id.code == 'RO')
      - Sale Order in EUR (foreign currency)
      - Downpayment invoice created in EUR then converted to company currency
        (simulating what the user does via the invoice form: change currency to RON
        and adjust the rate/prices via the onchange)
      - Exchange rate: 1 EUR = 5 company-currency units

    Key behaviours under test:
      1. _get_downpayment_line_price_unit converts invoice prices back to SO currency
         so the SO downpayment line is expressed in EUR, not in RON/company-currency.
      2. The final invoice created from the SO keeps move_type='out_invoice' (positive total).
      3. The onchange converts product-line prices correctly and uses the original
         downpayment invoice price for deduction lines.
      4. Both methods are no-ops for non-RO companies or when currencies already match.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.env.ref("base.ro")

        # Fixed test date so currency rates are deterministic
        cls.test_date = fields.Date.to_date("2025-12-01")

        cls.eur = cls.env.ref("base.EUR")
        cls.eur.active = True

        # EUR rate 0.2 → 1 / 0.2 = 5 company-currency units per EUR
        existing = cls.eur.rate_ids.filtered(
            lambda r: r.name == cls.test_date
            and r.company_id == cls.env.company
        )
        if existing:
            existing.rate = 0.2
        else:
            cls.eur.rate_ids = [
                Command.create(
                    {
                        "name": cls.test_date,
                        "rate": 0.2,
                        "company_id": cls.env.company.id,
                    }
                )
            ]

        cls.test_product = cls.env["product.product"].create(
            {
                "name": "Test Service",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 200.0,
                "taxes_id": [Command.clear()],
            }
        )

        cls.test_partner = cls.env["res.partner"].create({"name": "Test RO Partner"})

        # Enable pricelists so we can create SOs in EUR
        pricelist_group = cls.env.ref(
            "product.group_sale_pricelist", raise_if_not_found=False
        )
        if pricelist_group and pricelist_group not in cls.env.user.group_ids:
            cls.env.user.group_ids = [(4, pricelist_group.id)]

        cls.eur_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "EUR Test Pricelist",
                "currency_id": cls.eur.id,
                "company_id": cls.env.company.id,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_confirmed_so(self, price_unit=200.0):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.test_partner.id,
                "pricelist_id": self.eur_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "product_uom_qty": 1,
                            "price_unit": price_unit,
                            "tax_id": [Command.clear()],
                        }
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def _make_downpayment(self, so, amount_eur):
        """Create a fixed-amount downpayment invoice (draft) from a SO."""
        ctx = {
            "active_model": "sale.order",
            "active_ids": [so.id],
            "active_id": so.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        wizard = self.env["sale.advance.payment.inv"].with_context(ctx).create(
            {"advance_payment_method": "fixed", "fixed_amount": amount_eur}
        )
        wizard.create_invoices()
        return so.invoice_ids.filtered(lambda m: m.state == "draft")

    def _convert_and_post_dp(self, dp_invoice, company_currency_price):
        """
        Simulate what the user does on the downpayment invoice:
          - change currency to company currency
          - manually set the line price (result of the onchange * rate)
          - confirm (post) the invoice
        """
        company_currency = self.env.company.currency_id
        dp_line = dp_invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        dp_invoice.write(
            {"currency_id": company_currency.id, "invoice_date": self.test_date}
        )
        dp_line.price_unit = company_currency_price
        dp_invoice.action_post()

    # ------------------------------------------------------------------
    # Tests: SaleOrderLine._get_downpayment_line_price_unit
    # ------------------------------------------------------------------

    def test_downpayment_price_unit_converted_to_so_currency(self):
        """
        RO company, SO in EUR, dp invoice posted in company currency.
        _get_downpayment_line_price_unit must return the EUR equivalent:
          500 company-currency / 5 = 100 EUR  (not 500).
        """
        so = self._create_confirmed_so(200.0)
        dp = self._make_downpayment(so, 100.0)
        self._convert_and_post_dp(dp, 500.0)

        dp_so_line = so.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(len(dp_so_line), 1)

        result = dp_so_line._get_downpayment_line_price_unit(self.env["account.move"])
        self.assertAlmostEqual(
            result,
            100.0,
            places=2,
            msg="Must return 100 EUR, not 500 company-currency",
        )

    def test_same_currency_no_conversion(self):
        """
        SO and dp invoice in the same currency (EUR): amount returned as-is.
        """
        so = self._create_confirmed_so(200.0)
        dp = self._make_downpayment(so, 100.0)
        dp.invoice_date = self.test_date
        dp.action_post()

        dp_so_line = so.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        result = dp_so_line._get_downpayment_line_price_unit(self.env["account.move"])
        self.assertAlmostEqual(result, 100.0, places=2)

    def test_non_ro_company_uses_standard_behavior(self):
        """
        Non-RO company: falls back to Odoo standard (sum of price_unit, no conversion).
        500 company-currency is returned as-is.
        """
        self.env.company.country_id = self.env.ref("base.us")

        so = self._create_confirmed_so(200.0)
        dp = self._make_downpayment(so, 100.0)
        self._convert_and_post_dp(dp, 500.0)

        dp_so_line = so.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        result = dp_so_line._get_downpayment_line_price_unit(self.env["account.move"])
        self.assertAlmostEqual(
            result,
            500.0,
            places=2,
            msg="Non-RO company must return unconverted amount (500)",
        )

    # ------------------------------------------------------------------
    # Integration test
    # ------------------------------------------------------------------

    def test_final_invoice_not_switched_to_credit_note(self):
        """
        Full flow: SO 200 EUR, dp invoice 100 EUR converted to 500 company-currency.
        Without the fix:  200 EUR − 500 EUR = −300  → credit note.
        With the fix:     200 EUR − 100 EUR =  100  → out_invoice.
        """
        so = self._create_confirmed_so(200.0)
        dp = self._make_downpayment(so, 100.0)
        self._convert_and_post_dp(dp, 500.0)

        final = so._create_invoices(final=True)

        self.assertEqual(
            final.move_type,
            "out_invoice",
            "Final invoice must remain out_invoice, not switch to credit note",
        )
        self.assertGreater(
            final.amount_total,
            0,
            "Final invoice total must be positive",
        )

    # ------------------------------------------------------------------
    # Tests: AccountMove._onchange_currency_rate_to_invoice_line
    # ------------------------------------------------------------------

    def test_onchange_converts_product_line_price(self):
        """
        RO company, SO in EUR, invoice currency changed to company-currency at rate 5.
        Onchange must set price_unit = 200 EUR * 5 = 1000 company-currency.
        """
        so = self._create_confirmed_so(200.0)
        invoice = so._create_invoices()
        company_currency = self.env.company.currency_id

        invoice.currency_id = company_currency
        invoice.invoice_currency_rate = 5.0
        invoice._onchange_currency_rate_to_invoice_line()

        product_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        self.assertAlmostEqual(
            product_lines[0].price_unit,
            1000.0,
            places=2,
            msg="200 EUR * 5 = 1000 company-currency",
        )

    def test_onchange_skipped_for_non_ro_company(self):
        """
        Non-RO company: onchange must not modify any line prices.
        """
        self.env.company.country_id = self.env.ref("base.us")

        so = self._create_confirmed_so(200.0)
        invoice = so._create_invoices()
        company_currency = self.env.company.currency_id

        lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        original_price = lines[0].price_unit

        invoice.currency_id = company_currency
        invoice.invoice_currency_rate = 5.0
        invoice._onchange_currency_rate_to_invoice_line()

        self.assertAlmostEqual(lines[0].price_unit, original_price, places=2)

    def test_onchange_skipped_when_currencies_match(self):
        """
        When SO and invoice currency are both EUR, onchange must not touch prices.
        """
        so = self._create_confirmed_so(200.0)
        invoice = so._create_invoices()

        lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        original_price = lines[0].price_unit

        invoice.invoice_currency_rate = 5.0
        invoice._onchange_currency_rate_to_invoice_line()

        self.assertAlmostEqual(lines[0].price_unit, original_price, places=2)

    def test_onchange_downpayment_line_uses_original_invoice_price(self):
        """
        On the final invoice, the downpayment deduction line must use the price
        from the original dp invoice (500 company-currency), not SO price * rate.
        This ensures the deduction exactly offsets what was already billed.
        """
        so = self._create_confirmed_so(200.0)
        dp = self._make_downpayment(so, 100.0)
        self._convert_and_post_dp(dp, 500.0)

        final = so._create_invoices(final=True)
        company_currency = self.env.company.currency_id

        final.currency_id = company_currency
        final.invoice_currency_rate = 5.0
        final._onchange_currency_rate_to_invoice_line()

        dp_deduction = final.invoice_line_ids.filtered(
            lambda l: not l.display_type
            and l.sale_line_ids
            and l.sale_line_ids[0].is_downpayment
        )
        self.assertEqual(len(dp_deduction), 1)
        self.assertAlmostEqual(
            dp_deduction[0].price_unit,
            500.0,
            places=2,
            msg="Deduction line must use original dp invoice price (500)",
        )

    # ------------------------------------------------------------------
    # Scenario 2: SO in company currency (RON), invoice in EUR
    # ------------------------------------------------------------------
    # Company: RO, currency = company_currency (simulates RON)
    # SO: 1000 company_currency  (e.g. 1000 RON)
    # Downpayment invoice: 500 company_currency → converted to EUR at rate 0.2
    #   → 100 EUR  (invoice is in EUR)
    # Storno (credit note): reversal of the 100 EUR downpayment invoice
    # After storno, the net advance = 0, so the final invoice is for the full 1000.
    #
    # Rate from setUpClass: EUR.rate = 0.2  →  1 EUR = 5 company_currency units
    #   company_currency._convert(500, EUR)  = 500 * 0.2 = 100 EUR
    #   EUR._convert(100, company_currency)  = 100 * 5   = 500 company_currency
    # ------------------------------------------------------------------

    def _create_confirmed_so_company_currency(self, price_unit=1000.0):
        """SO in company currency (no pricelist needed)."""
        so = self.env["sale.order"].create(
            {
                "partner_id": self.test_partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "product_uom_qty": 1,
                            "price_unit": price_unit,
                            "tax_id": [Command.clear()],
                        }
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def _convert_dp_to_eur_and_post(self, dp_invoice, eur_price):
        """
        Simulate: user changes dp invoice currency from company-currency to EUR
        and sets the line price to the EUR equivalent, then posts.
        """
        dp_line = dp_invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        dp_invoice.write(
            {"currency_id": self.eur.id, "invoice_date": self.test_date}
        )
        dp_line.price_unit = eur_price
        dp_invoice.action_post()

    def _create_storno(self, dp_invoice, dp_so_line):
        """
        Create and post a credit note (storno) for a downpayment invoice.
        Ensures the credit note lines are linked to the SO downpayment line
        (Odoo does not copy sale_line_ids when reversing, so we add it manually).
        """
        credit_note = dp_invoice._reverse_moves([{"invoice_date": self.test_date}])
        for cn_line in credit_note.invoice_line_ids.filtered(lambda l: not l.display_type):
            if not cn_line.sale_line_ids:
                cn_line.sale_line_ids = [Command.link(dp_so_line.id)]
        credit_note.action_post()
        return credit_note

    def test_so_company_currency_dp_in_eur_price_correct(self):
        """
        SO in company-currency (1000). Downpayment invoice posted in EUR (100 EUR).
        _get_downpayment_line_price_unit must return 500 company-currency (not 100 EUR).
        EUR._convert(100, company_currency) = 100 * 5 = 500.
        """
        so = self._create_confirmed_so_company_currency(1000.0)
        dp = self._make_downpayment(so, 500.0)
        self._convert_dp_to_eur_and_post(dp, 100.0)

        dp_so_line = so.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(len(dp_so_line), 1)

        result = dp_so_line._get_downpayment_line_price_unit(self.env["account.move"])
        self.assertAlmostEqual(
            result,
            500.0,
            places=2,
            msg="Must return 500 company-currency, not 100 EUR",
        )

    def test_so_company_currency_dp_storno_net_zero(self):
        """
        SO 1000 company-currency. Dp invoice 100 EUR (=500 company-currency).
        After storno (credit note 100 EUR), net = 0.
        Final invoice must be out_invoice for the full remaining amount.
        """
        so = self._create_confirmed_so_company_currency(1000.0)
        dp = self._make_downpayment(so, 500.0)
        self._convert_dp_to_eur_and_post(dp, 100.0)

        dp_so_line = so.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        # Sanity check before storno: SO shows 500 company-currency
        self.assertAlmostEqual(dp_so_line.price_unit, 500.0, places=2)

        # Storno: credit note for 100 EUR
        self._create_storno(dp, dp_so_line)

        # After storno: out_invoice (100 EUR) + out_refund (-100 EUR) = 0
        result = dp_so_line._get_downpayment_line_price_unit(self.env["account.move"])
        self.assertAlmostEqual(result, 0.0, places=2)

        # Final invoice: no deduction → full 1000 company-currency
        final = so._create_invoices(final=True)
        self.assertEqual(
            final.move_type,
            "out_invoice",
            "Final invoice must be out_invoice after full storno",
        )
        self.assertGreater(final.amount_total, 0)

    def test_onchange_so_company_currency_converts_to_eur(self):
        """
        SO in company-currency (1000). User changes invoice currency to EUR at rate 0.2.
        Onchange must set price_unit = 1000 * 0.2 = 200 EUR.
        """
        so = self._create_confirmed_so_company_currency(1000.0)
        invoice = so._create_invoices()

        invoice.currency_id = self.eur.id
        invoice.invoice_currency_rate = 0.2
        invoice._onchange_currency_rate_to_invoice_line()

        product_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
        self.assertAlmostEqual(
            product_lines[0].price_unit,
            200.0,
            places=2,
            msg="1000 company-currency * 0.2 = 200 EUR",
        )
