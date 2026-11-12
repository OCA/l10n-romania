# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestInvoiceCurrencyRate(AccountTestInvoicingCommon):
    """``l10n_ro_currency_rate`` is the inverse of the standard
    ``invoice_currency_rate``: 1 document currency = X company currency."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        # ``rate`` is "EUR for 1 RON": 0.2 -> 1 EUR = 5 RON, 0.25 -> 1 EUR = 4 RON
        cls.eur = cls.setup_other_currency(
            "EUR",
            rates=[("2025-01-01", 0.2), ("2025-06-01", 0.25)],
        )

    def _eur_invoice(self, invoice_date="2025-03-01", **kwargs):
        return self._create_invoice(
            invoice_date=invoice_date,
            currency_id=self.eur.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100)],
            **kwargs,
        )

    def test_rate_is_inverse_of_invoice_currency_rate(self):
        invoice = self._eur_invoice()
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.2)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 5.0)

    def test_rate_follows_invoice_date(self):
        invoice = self._eur_invoice()
        with Form(invoice) as move_form:
            move_form.invoice_date = "2025-07-01"
            # recomputed in the form already, before saving
            self.assertAlmostEqual(move_form.l10n_ro_currency_rate, 4.0)
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.25)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 4.0)

    def test_rate_follows_manual_rate_and_refresh(self):
        invoice = self._eur_invoice()
        with Form(invoice) as move_form:
            move_form.invoice_currency_rate = 0.16
            self.assertAlmostEqual(move_form.l10n_ro_currency_rate, 6.25)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 6.25)

        invoice.refresh_invoice_currency_rate()
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.2)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 5.0)

    def test_edit_ro_rate_updates_standard_rate(self):
        invoice = self._eur_invoice()
        with Form(invoice) as move_form:
            move_form.l10n_ro_currency_rate = 4.0
            # applied in the form already, before saving
            self.assertAlmostEqual(move_form.invoice_currency_rate, 0.25)
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.25)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 4.0)
        # the lines are converted with the new rate: 100 EUR * 4 = 400 RON
        line = invoice.invoice_line_ids
        self.assertAlmostEqual(line.currency_rate, 0.25)
        self.assertAlmostEqual(abs(line.balance), 400.0)

        # write() goes through the inverse as well
        invoice.l10n_ro_currency_rate = 5.0
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.2)
        self.assertAlmostEqual(abs(invoice.invoice_line_ids.balance), 500.0)

    def test_edit_ro_rate_keeps_precise_standard_rate(self):
        """Saving the form must not round a manual standard rate through the
        4-digit RO rate."""
        invoice = self._eur_invoice()
        with Form(invoice) as move_form:
            move_form.invoice_currency_rate = 0.201234
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.201234, places=6)
        invoice.l10n_ro_currency_rate = invoice.l10n_ro_currency_rate
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.201234, places=6)

    def test_edit_ro_rate_ignores_non_positive(self):
        invoice = self._eur_invoice()
        with Form(invoice) as move_form:
            move_form.l10n_ro_currency_rate = 0
            self.assertAlmostEqual(move_form.l10n_ro_currency_rate, 5.0)
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.2)

    def test_rate_in_company_currency_and_entry(self):
        invoice = self._create_invoice(
            invoice_date="2025-03-01",
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100)],
        )
        self.assertEqual(invoice.currency_id, self.env.company.currency_id)
        self.assertAlmostEqual(invoice.l10n_ro_currency_rate, 1.0)

        # invoice_currency_rate is not computed on misc entries
        entry = self.env["account.move"].create(
            {"move_type": "entry", "date": "2025-03-01", "currency_id": self.eur.id}
        )
        self.assertAlmostEqual(entry.l10n_ro_currency_rate, 1.0)

    def test_report_prints_inverse_rate(self):
        # The "Taxes RON" box holding the exchange rate is printed only for
        # taxed customer invoices when this company option is enabled.
        self.env.company.display_invoice_tax_company_currency = True
        invoice = self._create_invoice(
            invoice_date="2025-03-01",
            currency_id=self.eur.id,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_sale_a)
            ],
            post=True,
        )
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("account.account_invoices", invoice.ids)[0]
            .decode()
        )
        self.assertIn("Exchange Rate", html)
        self.assertIn("5.0000", html)
        self.assertNotIn("0.20000", html)
