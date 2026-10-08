# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Coverage for the Romanian POS refund.

A refunded receipt has to leave the shop as a credit note plus a payment
disposal, and the cash behind that disposal must leave the till exactly once:
the statement line carries it, so the POS payment has to be kept out of the
session's cash flow and out of its closing entry.
"""

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged("post_install", "-at_install")
class TestL10nRoPosRefund(CommonPosTest):
    @classmethod
    @CommonPosTest.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.config = cls.pos_config_usd
        cls.product = cls.ten_dollars_no_tax.product_variant_id
        cls.cash_journal = cls.cash_payment_method.journal_id

        # A Romanian credit note carries an e-Factura (CIUS RO) document, and
        # that one refuses to be built over incomplete parties -- which is what
        # would otherwise turn the credit note into a proforma. Give both sides
        # everything it asks for, so the suite walks the real path.
        romania = cls.env.ref("base.ro")
        timis = cls.env.ref("base.RO_TM")
        cls.env.company.partner_id.write(
            {
                "country_id": romania.id,
                "state_id": timis.id,
                "street": "Str. Gheorghe Lazar 9",
                "city": "Timisoara",
                "zip": "300081",
                "vat": "RO39187746",
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "RO Customer",
                "country_id": romania.id,
                "state_id": timis.id,
                "street": "Bd. Revolutiei 1",
                "city": "Timisoara",
                "zip": "300054",
                "vat": "RO14399840",
            }
        )
        # CIUS RO also wants a tax on every line, and the shared fixture has
        # none; keep it for the money assertions and tax a copy for the rest.
        cls.taxed_product = cls.product.copy(
            {
                "name": "Ten with Romanian VAT",
                "available_in_pos": True,
                "taxes_id": [
                    Command.set(
                        cls.env["account.tax"]
                        .search(
                            [
                                ("company_id", "=", cls.env.company.id),
                                ("type_tax_use", "=", "sale"),
                            ],
                            limit=1,
                        )
                        .ids
                    )
                ],
            }
        )

    # ------------------------------------------------------------------ #
    # helpers                                                            #
    # ------------------------------------------------------------------ #

    def _session(self):
        if not self.config.current_session_id:
            self.config.open_ui()
        return self.config.current_session_id

    def _sale(self, partner=None, qty=1.0, product=None):
        product = product or self.product
        order, _refund = self.create_backend_pos_order(
            {
                "pos_config": self.config,
                "order_data": {"partner_id": partner.id if partner else False},
                "line_data": [{"product_id": product.id, "qty": qty}],
                "payment_data": [
                    {"payment_method_id": self.cash_payment_method.id},
                ],
            }
        )
        return order

    def _refund(self, order, payment_method=None, generate_pdf=False):
        refund = self.env["pos.order"].browse(order.refund()["res_id"])
        context = {
            "active_ids": refund.ids,
            "active_id": refund.id,
            # The PDF is not what most of these tests are about.
            "generate_pdf": generate_pdf,
        }
        wizard = (
            self.env["pos.make.payment"]
            .with_context(**context)
            .create(
                {
                    "payment_method_id": (
                        payment_method or self.cash_payment_method
                    ).id,
                    "amount": refund.amount_total,
                }
            )
        )
        wizard.with_context(**context).check()
        return refund

    # ------------------------------------------------------------------ #
    # the customer is not optional                                        #
    # ------------------------------------------------------------------ #

    def test_a_refund_without_a_customer_is_refused(self):
        # Both documents the refund owes the customer are issued in their
        # name, so there is nothing to fall back on.
        order = self._sale()
        with self.assertRaises(ValidationError):
            self._refund(order)

    def test_a_plain_sale_still_needs_no_customer(self):
        order = self._sale()
        self.assertEqual(order.state, "paid")
        self.assertFalse(order.partner_id)

    # ------------------------------------------------------------------ #
    # credit note                                                         #
    # ------------------------------------------------------------------ #

    def test_a_refund_issues_a_credit_note_on_the_pos_invoice_journal(self):
        refund = self._refund(self._sale(self.customer))

        credit_note = refund.account_move
        self.assertTrue(refund.to_invoice, "Invoicing a refund is not optional")
        self.assertEqual(credit_note.move_type, "out_refund")
        self.assertEqual(credit_note.journal_id, self.config.invoice_journal_id)
        self.assertEqual(credit_note.partner_id, self.customer)
        self.assertEqual(credit_note.amount_total, 10.0)

    # ------------------------------------------------------------------ #
    # payment disposal                                                    #
    # ------------------------------------------------------------------ #

    def test_the_cash_refunded_gets_its_own_statement_line(self):
        refund = self._refund(self._sale(self.customer))

        disposal = refund.l10n_ro_payment_disposal_id
        self.assertTrue(disposal, "The cash returned needs a payment disposal")
        self.assertEqual(disposal.journal_id, self.cash_journal)
        self.assertEqual(disposal.pos_session_id, refund.session_id)
        self.assertEqual(disposal.partner_id, self.customer)
        self.assertEqual(disposal.amount, -10.0, "Cash out of the till")
        self.assertEqual(refund.payment_ids.l10n_ro_payment_disposal_id, disposal)

    def test_the_payment_disposal_settles_the_credit_note(self):
        refund = self._refund(self._sale(self.customer))

        credit_note = refund.account_move
        self.assertEqual(credit_note.payment_state, "paid")
        receivable = credit_note.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        counterpart = refund.l10n_ro_payment_disposal_id.move_id.line_ids.filtered(
            lambda line: line.account_id == receivable.account_id
        )
        self.assertTrue(counterpart.reconciled)
        self.assertTrue(receivable.reconciled)

    def test_the_refund_payment_makes_no_pos_payment_move(self):
        # Core pairs an invoiced POS payment with a payment move; here the
        # statement line is what settles the credit note.
        refund = self._refund(self._sale(self.customer))
        self.assertFalse(refund.payment_ids.account_move_id)

    def test_a_card_refund_keeps_the_standard_flow(self):
        refund = self._refund(
            self._sale(self.customer), payment_method=self.bank_payment_method
        )
        self.assertFalse(refund.l10n_ro_payment_disposal_id)
        self.assertTrue(refund.payment_ids.account_move_id)
        self.assertEqual(refund.account_move.move_type, "out_refund")

    def test_the_credit_note_is_a_real_pdf(self):
        sale = self._sale(self.customer, product=self.taxed_product)
        refund = self._refund(sale, generate_pdf=True)

        attachment = refund.account_move.invoice_pdf_report_id
        self.assertTrue(attachment, "The credit note needs its own PDF")
        self.assertNotIn("proforma", attachment.name)

    def test_a_refund_is_refused_when_only_a_proforma_can_be_issued(self):
        # Core attaches a proforma and carries on when the documents cannot be
        # generated. A proforma reverses nothing, so the refund goes back.
        order = self._sale(self.customer, product=self.taxed_product)

        def refuse_documents(records, invoice, invoice_data):
            invoice_data["error"] = {
                "error_title": "The county is missing on the customer",
            }

        with (
            patch.object(
                type(self.env["account.move.send"]),
                "_hook_invoice_document_before_pdf_report_render",
                refuse_documents,
            ),
            self.assertRaises(UserError) as caught,
            self.cr.savepoint(),
        ):
            self._refund(order, generate_pdf=True)

        self.assertIn("county is missing", str(caught.exception))

    def test_a_refund_survives_an_e_factura_that_cannot_reach_the_spv(self):
        # The upload is retried from the back office; a shop with no ANAF
        # credentials yet must still be able to hand over a credit note.
        order = self._sale(self.customer, product=self.taxed_product)

        def refuse_upload(records, invoices_data):
            for invoice_data in invoices_data.values():
                invoice_data["error"] = {
                    "error_title": "Error when sending CIUS-RO E-Factura to the SPV",
                    "errors": ["Romanian access token not found."],
                }

        with patch.object(
            type(self.env["account.move.send"]),
            "_call_web_service_after_invoice_pdf_render",
            refuse_upload,
        ):
            refund = self._refund(order, generate_pdf=True)

        self.assertTrue(refund.account_move.invoice_pdf_report_id)
        self.assertTrue(refund.l10n_ro_payment_disposal_id)

    # ------------------------------------------------------------------ #
    # the payment disposal reaches the printer                            #
    # ------------------------------------------------------------------ #

    def test_the_payment_disposal_report_is_offered_to_the_pos(self):
        refund = self._refund(self._sale(self.customer))
        action = refund.l10n_ro_get_payment_disposal_report()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(
            action["context"]["active_ids"],
            refund.l10n_ro_payment_disposal_id.ids,
        )

    def test_a_refund_without_a_disposal_offers_no_report(self):
        refund = self._refund(
            self._sale(self.customer), payment_method=self.bank_payment_method
        )
        self.assertFalse(refund.l10n_ro_get_payment_disposal_report())

    # ------------------------------------------------------------------ #
    # the cash only leaves the till once                                  #
    # ------------------------------------------------------------------ #

    def test_the_cash_balance_counts_the_refund_once(self):
        session = self._session()
        self._sale(self.customer)
        session.invalidate_recordset()
        before = session.cash_register_balance_end

        self._refund(self._sale(self.customer))
        session.invalidate_recordset()

        # One sale paid in (+10) and one refund paid out (-10) since `before`.
        self.assertAlmostEqual(session.cash_register_balance_end, before, places=2)

    def test_the_closing_control_counts_the_refund_once(self):
        session = self._session()
        self._sale(self.customer)
        self._refund(self._sale(self.customer))
        session.invalidate_recordset()

        cash = session.get_closing_control_data()["default_cash_details"]
        self.assertAlmostEqual(cash["amount"], session.cash_register_balance_end, 2)

    def test_the_closing_entry_ignores_the_refunded_cash(self):
        session = self._session()
        refund = self._refund(self._sale(self.customer))
        session.invalidate_recordset()

        data = session._accumulate_amounts({})
        method = self.cash_payment_method
        cash = data["combine_receivables_cash"].get(method, {"amount": 0.0})
        # Only the sale that funded the refund is left in the bucket.
        self.assertAlmostEqual(cash["amount"], 10.0, places=2)
        self.assertNotIn(method, data["combine_invoice_receivables"])
        self.assertFalse(data["combine_inv_payment_receivable_lines"].get(method))
        self.assertTrue(refund.l10n_ro_payment_disposal_id)

    def test_the_session_closes_balanced(self):
        session = self._session()
        self._sale(self.customer)
        self._refund(self._sale(self.customer))
        session.invalidate_recordset()

        session.post_closing_cash_details(session.cash_register_balance_end)
        session.close_session_from_ui()
        self.assertEqual(session.state, "closed")
        self.assertTrue(session.move_id)
        self.assertEqual(session.move_id.state, "posted")
