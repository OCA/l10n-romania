# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
from datetime import date, timedelta

from odoo import tools
from odoo.tests.common import TransactionCase


class TestVATonpayment(TransactionCase):
    """Run test for VAT on payment."""

    def setUp(self):
        super(TestVATonpayment, self).setUp()
        self.partner_anaf_model = self.env["res.partner.anaf"]
        self.partner_model = self.env["res.partner"]
        self.invoice_model = self.env["account.move"]
        self.fbr_partner = self.partner_model.create(
            {"name": "FBR", "vat": "RO30834857"}
        )
        self.lxt_partner = self.partner_model.create(
            {"name": "Luxmet", "vat": "RO16507426"}
        )
        default_line_account = self.env["account.account"].search(
            [
                ("internal_type", "=", "other"),
                ("deprecated", "=", False),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        self.invoice_line = [
            (
                0,
                False,
                {
                    "name": "Test description #1",
                    "product_id": self.env.ref("product.product_delivery_01").id,
                    "account_id": default_line_account.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                },
            )
        ]
        self.invoice = self.invoice_model.create(
            {
                "partner_id": self.lxt_partner.id,
                "move_type": "in_invoice",
                "invoice_line_ids": self.invoice_line,
            }
        )
        self.fp_model = self.env["account.fiscal.position"]
        self.fptvainc = self.fp_model.search(
            [
                ("name", "ilike", "Regim TVA la Incasare"),
                ("company_id", "=", self.env.company.id),
            ]
        )

    def test_download_data(self):
        """Test download file and partner link."""
        data_dir = tools.config["data_dir"]
        prev_day = date.today() - timedelta(1)
        self.partner_anaf_model._download_anaf_data(prev_day)
        istoric = os.path.join(data_dir, "istoric.txt")
        self.assertEqual(os.path.exists(istoric), True)
        self.partner_anaf_model._download_anaf_data()
        self.assertEqual(os.path.exists(istoric), True)

    def test_update_partner_data(self):
        """Test download file and partner link."""
        self.partner_model._update_vat_payment_all()
        self.assertEqual(len(self.fbr_partner.anaf_history), 2)
        self.assertEqual(self.fbr_partner.vat_on_payment, False)
        self.assertEqual(len(self.lxt_partner.anaf_history), 1)
        self.assertEqual(self.lxt_partner.vat_on_payment, True)

    def test_invoice_fp(self):
        """Test download file and partner link."""
        self.invoice._onchange_partner_id()
        self.assertEqual(self.invoice.fiscal_position_id, self.fptvainc)
