# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMove(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.l10n_ro_accounting = True
        cls.currency = cls.env["res.currency"].search([("name", "=", "RON")])
        cls.inv_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Invoices",
                "code": "INV",
                "implementation": "no_gap",
                "prefix": "FCT/",
                "padding": 5,
                "number_increment": 1,
                "number_next_actual": 1,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test sale",
                "code": "TST",
                "type": "sale",
                "l10n_ro_journal_sequence_id": cls.inv_sequence.id,
                "currency_id": cls.currency.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.category = cls.env["product.category"].create(
            {
                "name": "Test category",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test sale",
                "categ_id": cls.category.id,
                "list_price": 10,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test sale",
            }
        )
        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "tax_19",
                "amount_type": "percent",
                "amount": 19,
                "type_tax_use": "sale",
                "sequence": 19,
                "company_id": cls.env.company.id,
            }
        )
        cls.invoice1 = cls.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": cls.partner.id,
                    "currency_id": cls.currency.id,
                    "journal_id": cls.journal.id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product.id,
                                "name": "Test sale",
                                "quantity": 1,
                                "price_unit": 10.00,
                                "tax_ids": [(6, 0, cls.tax_19.ids)],
                            },
                        ),
                    ],
                }
            ]
        )
        cls.invoice2 = cls.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": cls.partner.id,
                    "currency_id": cls.currency.id,
                    "journal_id": cls.journal.id,
                    "invoice_line_ids": [
                        (
                            0,
                            None,
                            {
                                "product_id": cls.product.id,
                                "name": "Test sale",
                                "quantity": 1,
                                "price_unit": 10.00,
                                "tax_ids": [(6, 0, cls.tax_19.ids)],
                            },
                        ),
                    ],
                }
            ]
        )

    def test_l10n_ro_invoice_number(self):
        invoice1 = self.invoice1
        invoice1.action_post()
        self.assertEqual(invoice1.name, "FCT/00001")
        invoice2 = self.invoice2
        invoice2.action_post()
        self.assertEqual(invoice2.name, "FCT/00002")
