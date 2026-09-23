# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
import shutil
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from odoo import tools
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestVATonpayment(AccountTestInvoicingCommon):
    """Run test for VAT on payment."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.partner_anaf_model = cls.env["l10n.ro.res.partner.anaf"]
        cls.partner_model = cls.env["res.partner"]
        cls.invoice_model = cls.env["account.move"]

        cls.fp_model = cls.env["account.fiscal.position"]
        cls.fptvainc = cls.env.company.l10n_ro_property_vat_on_payment_position_id
        if not cls.fptvainc:
            cls.fptvainc = cls.fp_model.create(
                {
                    "name": "Sistem de colectare TVA",
                    "company_id": cls.env.company.id,
                }
            )
            cls.env.company.l10n_ro_property_vat_on_payment_position_id = cls.fptvainc

        cls.fbr_partner = cls.partner_model.create(
            {
                "name": "FBR",
                "vat": "RO30834857",
                "country_id": cls.env.ref("base.ro").id,
                "is_company": True,
                "l10n_ro_vat_subjected": True,
            }
        )
        cls.lxt_partner = cls.partner_model.create(
            {
                "name": "Luxmet",
                "vat": "RO16507426",
                "country_id": cls.env.ref("base.ro").id,
                "is_company": True,
                "l10n_ro_vat_subjected": True,
            }
        )
        default_line_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("deprecated", "=", False),
                ("company_ids", "in", cls.env.company.ids),
            ],
            limit=1,
        )
        cls.invoice_line = [
            (
                0,
                False,
                {
                    "name": "Test description #1",
                    "product_id": cls.env.ref("product.product_delivery_01").id,
                    "account_id": default_line_account.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                },
            )
        ]
        cls.invoice = cls.invoice_model.create(
            {
                "partner_id": cls.lxt_partner.id,
                "move_type": "in_invoice",
                "invoice_line_ids": cls.invoice_line,
            }
        )

        data_dir = tools.config["data_dir"]
        istoric_file = os.path.join(data_dir, "istoric.txt")

        test_file = file_path("l10n_ro_vat_on_payment/tests/istoric.txt")
        shutil.copyfile(test_file, istoric_file)

    def _mock_anaf_request(self):
        """Mock ANAF request to avoid external HTTP calls during tests."""
        # Create a sample zip file content with the historic.txt file
        test_file_path = file_path("l10n_ro_vat_on_payment/tests/istoric.txt")

        # Create a BytesIO object to simulate zip file content
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.write(test_file_path, "istoric.txt")
        zip_buffer.seek(0)

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_buffer.getvalue()

        return mock_response

    @patch("requests.get")
    def test_download_data(self, mock_get):
        """Test download file and partner link."""
        mock_get.return_value = self._mock_anaf_request()

        data_dir = tools.config["data_dir"]
        istoric = os.path.join(data_dir, "istoric.txt")
        prev_day = date.today() - timedelta(1)

        self.partner_anaf_model._download_anaf_data(prev_day)
        self.assertTrue(mock_get.called)
        self.assertTrue(os.path.exists(istoric))

        self.partner_anaf_model._download_anaf_data()
        self.assertTrue(os.path.exists(istoric))

    @patch("requests.get")
    def test_update_partner_data(self, mock_get):
        """Test download file and partner link."""
        mock_get.return_value = self._mock_anaf_request()

        self.partner_model._update_vat_payment_all()
        # FBR was registered on 2013-02-01 and removed from the register
        # on 2013-08-01, so it is not on VAT on payment any more.
        self.assertEqual(len(self.fbr_partner.l10n_ro_anaf_history), 2)
        self.assertEqual(self.fbr_partner.l10n_ro_vat_on_payment, False)
        self.assertEqual(
            self.fbr_partner.with_context(
                check_date=date(2013, 4, 23)
            )._check_vat_on_payment(),
            True,
        )
        self.assertEqual(
            self.fbr_partner.with_context(
                check_date=date(2013, 8, 1)
            )._check_vat_on_payment(),
            False,
        )
        self.assertEqual(len(self.lxt_partner.l10n_ro_anaf_history), 1)
        self.assertEqual(self.lxt_partner.l10n_ro_vat_on_payment, True)

    def _create_anaf_history(self, partner, vat, lines):
        """Create ANAF records for ``vat`` and refresh the partner history."""
        for index, vals in enumerate(lines):
            self.partner_anaf_model.create(
                dict(vals, anaf_id=f"test-{vat}-{index}", vat=vat)
            )
        # l10n_ro_anaf_history is a computed field that does not refresh on
        # its own when new l10n.ro.res.partner.anaf records appear for this
        # vat; recompute it so the result does not depend on cache state.
        partner._compute_l10n_ro_anaf_history()

    def test_check_vat_on_payment_reregistration_after_removal(self):
        """A removal followed by a later re-registration must leave the
        partner on VAT on payment: the most recent ANAF operation wins."""
        partner = self.partner_model.create(
            {
                "name": "Test Reregistered SRL",
                "vat": "RO24148595",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        self._create_anaf_history(
            partner,
            "24148595",
            [
                {
                    "start_date": date(2024, 3, 1),
                    "end_date": date(2025, 8, 1),
                    "publish_date": date(2025, 7, 20),
                    "operation_date": date(2025, 7, 15),
                    "operation_type": "D",
                },
                {
                    "start_date": date(2025, 9, 1),
                    "end_date": False,
                    "publish_date": date(2025, 8, 25),
                    "operation_date": date(2025, 8, 20),
                    "operation_type": "I",
                },
            ],
        )
        self.assertTrue(
            partner.with_context(
                no_insert=True, check_date=date.today()
            )._check_vat_on_payment(),
            "A re-registration published after a removal must win over it.",
        )

    def test_check_vat_on_payment_reregistration_on_removal_day(self):
        """A re-registration starting the very day the removal ends leaves
        no gap, so the partner is on VAT on payment on that day too. The
        register holds 102 such partners; this one mirrors CUI 22440."""
        partner = self.partner_model.create(
            {
                "name": "Test Same Day SRL",
                "vat": "RO20000013",
                "country_id": self.env.ref("base.ro").id,
                "is_company": True,
                "l10n_ro_vat_subjected": True,
            }
        )
        self._create_anaf_history(
            partner,
            "20000013",
            [
                {
                    "start_date": date(2013, 1, 1),
                    "end_date": date(2021, 4, 1),
                    "publish_date": date(2021, 3, 18),
                    "operation_date": date(2021, 3, 17),
                    "operation_type": "D",
                },
                {
                    "start_date": date(2021, 4, 1),
                    "end_date": False,
                    "publish_date": date(2021, 3, 20),
                    "operation_date": date(2021, 3, 19),
                    "operation_type": "I",
                },
            ],
        )
        for check_date, expected in (
            (date(2021, 3, 31), True),
            (date(2021, 4, 1), True),
            (date.today(), True),
        ):
            self.assertEqual(
                partner.with_context(
                    no_insert=True, check_date=check_date
                )._check_vat_on_payment(),
                expected,
                f"wrong VAT on payment status at {check_date}",
            )

    def test_check_vat_on_payment_removal_is_last_operation(self):
        """Mirror case: when the removal is the most recent operation it
        must win over the still open registration record it closes, which
        keeps the same start_date and an empty end_date."""
        partner = self.partner_model.create(
            {
                "name": "Test Removed SRL",
                "vat": "RO12345674",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        self._create_anaf_history(
            partner,
            "12345674",
            [
                {
                    "start_date": date(2024, 3, 1),
                    "end_date": False,
                    "publish_date": date(2024, 3, 5),
                    "operation_date": date(2024, 3, 4),
                    "operation_type": "I",
                },
                {
                    "start_date": date(2024, 3, 1),
                    "end_date": date(2025, 8, 1),
                    "publish_date": date(2025, 7, 20),
                    "operation_date": date(2025, 7, 15),
                    "operation_type": "D",
                },
            ],
        )
        self.assertFalse(
            partner.with_context(
                no_insert=True, check_date=date.today()
            )._check_vat_on_payment(),
            "The removal closing the registration must clear the flag.",
        )
        # The removal is also the most recent operation for a date before
        # it was performed; there, the period it defines was still open.
        self.assertTrue(
            partner.with_context(
                no_insert=True, check_date=date(2025, 1, 1)
            )._check_vat_on_payment(),
            "Before its end_date the partner was still on VAT on payment.",
        )

    def test_check_vat_on_payment_undated_line_does_not_shadow(self):
        """A record without an operation date must not outrank a dated
        one: the database sorts NULLs first on a descending order, which
        would otherwise pick the record at random."""
        partner = self.partner_model.create(
            {
                "name": "Test Undated SRL",
                "vat": "RO20000005",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        self._create_anaf_history(
            partner,
            "20000005",
            [
                {
                    "start_date": date(2024, 1, 1),
                    "end_date": False,
                    "operation_type": "I",
                },
                {
                    "start_date": date(2024, 1, 1),
                    "end_date": date(2024, 6, 1),
                    "publish_date": date(2024, 5, 25),
                    "operation_date": date(2024, 5, 20),
                    "operation_type": "D",
                },
            ],
        )
        self.assertFalse(
            partner.with_context(
                no_insert=True, check_date=date.today()
            )._check_vat_on_payment(),
            "The dated removal must win over the undated registration.",
        )

    def test_invoice_fp(self):
        """Test download file and partner link."""
        if not self.invoice.partner_id.l10n_ro_vat_on_payment:
            self.lxt_partner.l10n_ro_vat_on_payment = True
        self.invoice._onchange_partner_id()
        self.assertEqual(self.invoice.fiscal_position_id, self.fptvainc)
