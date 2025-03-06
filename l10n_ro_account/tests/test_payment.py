# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPayment(AccountTestInvoicingCommon):
    def setUp(self):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUp(chart_template_ref=ro_template_ref)

        self.env.company.l10n_ro_accounting = True
        self.partner_person = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "company_type": "person",
            }
        )
        self.partner_company = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "company_type": "company",
            }
        )
        self.journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "cash",
            }
        )
        self.invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_company.id,
                "move_type": "out_invoice",
                "date": "2021-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test invoice line",
                            "quantity": 1,
                            "price_unit": 15000,
                        },
                    )
                ],
            }
        )
        self.invoice.action_post()

    def test_create_payment_error(self):
        with self.assertRaises(ValidationError):
            self.env["account.payment"].create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": self.partner_company.id,
                    "amount": 6000,
                    "journal_id": self.journal.id,
                }
            )
        with self.assertRaises(ValidationError):
            self.env["account.payment"].create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": self.partner_person.id,
                    "amount": 11000,
                    "journal_id": self.journal.id,
                }
            )

    def test_payment_write_error(self):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_person.id,
                "amount": 6000,
                "journal_id": self.journal.id,
            }
        )
        with self.assertRaises(ValidationError):
            payment.write({"amount": 11000})

    def test_create_payment_register_error(self):
        register = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=[self.invoice.id]
        )

        payment_register = register.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_company.id,
                "amount": 6000,
                "journal_id": self.journal.id,
            }
        )
        with self.assertRaises(ValidationError):
            payment_register.action_create_payments()

        payment_register = register.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_person.id,
                "amount": 11000,
                "journal_id": self.journal.id,
            }
        )
        with self.assertRaises(ValidationError):
            payment_register.action_create_payments()
