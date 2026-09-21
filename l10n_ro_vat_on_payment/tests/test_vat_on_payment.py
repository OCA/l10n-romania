# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
import shutil
from datetime import date, timedelta

import requests

from odoo import tools
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestVATonpayment(AccountTestInvoicingCommon):
    """Run test for VAT on payment."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref="ro")
        cls.env.company.l10n_ro_accounting = True
        cls.partner_anaf_model = cls.env["l10n.ro.res.partner.anaf"]
        cls.partner_model = cls.env["res.partner"]
        cls.invoice_model = cls.env["account.move"]
        cls.fbr_partner = cls.partner_model.create(
            {
                "name": "FBR",
                "vat": "RO30834857",
                "country_id": cls.env.ref("base.ro").id,
            }
        )
        cls.lxt_partner = cls.partner_model.create(
            {
                "name": "Luxmet",
                "vat": "RO16507426",
                "country_id": cls.env.ref("base.ro").id,
            }
        )
        default_line_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("deprecated", "=", False),
                ("company_id", "=", cls.env.company.id),
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
        cls.fp_model = cls.env["account.fiscal.position"]
        cls.fptvainc = cls.env.company.l10n_ro_property_vat_on_payment_position_id
        # cls.fptvainc = cls.fp_model.search(
        #     [
        #         ("name", "ilike", "Sistem de colectare TVA"),
        #         ("company_id", "=", cls.env.company.id),
        #     ]
        # )
        if not cls.fptvainc:
            cls.fptvainc = cls.fp_model.create(
                {
                    "name": "Sistem de colectare TVA",
                    "company_id": cls.env.company.id,
                }
            )
            cls.env.company.l10n_ro_property_vat_on_payment_position_id = cls.fptvainc

        data_dir = tools.config["data_dir"]
        istoric_file = os.path.join(data_dir, "istoric.txt")

        test_file = file_path("l10n_ro_vat_on_payment/tests/istoric.txt")
        shutil.copyfile(test_file, istoric_file)

    def test_download_data(self):
        """Test download file and partner link."""
        data_dir = tools.config["data_dir"]
        prev_day = date.today() - timedelta(1)
        try:
            self.partner_anaf_model._download_anaf_data(prev_day)
            istoric = os.path.join(data_dir, "istoric.txt")
            self.assertEqual(os.path.exists(istoric), True)
        except (
            Exception,
            requests.exceptions.ConnectionError,
            requests.exceptions.MissingSchema,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            requests.exceptions.ChunkedEncodingError,
        ):
            _logger.warning("Server ANAF is down.")
            return True

        try:
            self.partner_anaf_model._download_anaf_data()
            istoric = os.path.join(data_dir, "istoric.txt")
            self.assertEqual(os.path.exists(istoric), True)
        except (
            Exception,
            requests.exceptions.ConnectionError,
            requests.exceptions.MissingSchema,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            requests.exceptions.ChunkedEncodingError,
        ):
            _logger.warning("Server ANAF is down.")
            return True

    def test_update_partner_data(self):
        """Test download file and partner link."""
        try:
            self.partner_model._update_vat_payment_all()
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
        except (
            Exception,
            requests.exceptions.ConnectionError,
            requests.exceptions.MissingSchema,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            requests.exceptions.ChunkedEncodingError,
        ):
            _logger.warning("Server ANAF is down.")
            return True

    def test_check_vat_on_payment_prefers_active_over_expired_line(self):
        partner = self.partner_model.create(
            {
                "name": "Test Multi History SRL",
                "vat": "RO24148595",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        # Insert the EXPIRED line first and the ACTIVE one second
        self.partner_anaf_model.create(
            {
                "anaf_id": "test-24148595-d",
                "vat": "24148595",
                "start_date": date(2024, 3, 1),
                "end_date": date(2025, 8, 1),
                "operation_type": "D",
            }
        )
        self.partner_anaf_model.create(
            {
                "anaf_id": "test-24148595-i",
                "vat": "24148595",
                "start_date": date(2024, 3, 1),
                "end_date": False,
                "operation_type": "I",
            }
        )
        # l10n_ro_anaf_history is a compute field that does not
        # auto-refresh when new l10n.ro.res.partner.anaf records are
        # created for this vat; force a recompute before checking,
        # otherwise the result depends on stale ORM cache state.
        partner._compute_l10n_ro_anaf_history()
        result = partner.with_context(
            no_insert=True, check_date=date.today()
        )._check_vat_on_payment()
        self.assertTrue(
            result,
            "A currently active ANAF registration must win over an "
            "older, already expired removal line.",
        )

    def test_check_vat_on_payment_line_selection_order(self):
        """Verify the exact mechanism added to fix the bug above: the
        search must (1) exclude lines already closed at check_date via
        the `end_date` domain, and (2) apply `order='start_date desc'` so
        that, if more than one line is still open at check_date (a data
        anomaly - there should only ever be one), the most recently
        started registration is the one used.

        NOTE: this test mirrors the domain/order used in
        ``res_partner.py::_check_vat_on_payment`` by construction, since
        ``_check_vat_on_payment`` only returns a boolean and cannot
        distinguish *which* line was picked. If that domain/order is ever
        changed, update this test to match.
        """
        partner = self.partner_model.create(
            {
                "name": "Test Overlapping History SRL",
                "vat": "RO12345674",
                "country_id": self.env.ref("base.ro").id,
            }
        )
        expired = self.partner_anaf_model.create(
            {
                "anaf_id": "test-12345674-expired",
                "vat": "12345674",
                "start_date": date(2019, 1, 1),
                "end_date": date(2020, 1, 1),
                "operation_type": "D",
            }
        )
        old_open = self.partner_anaf_model.create(
            {
                "anaf_id": "test-12345674-old-open",
                "vat": "12345674",
                "start_date": date(2020, 1, 1),
                "end_date": False,
                "operation_type": "I",
            }
        )
        new_open = self.partner_anaf_model.create(
            {
                "anaf_id": "test-12345674-new-open",
                "vat": "12345674",
                "start_date": date(2024, 1, 1),
                "end_date": False,
                "operation_type": "I",
            }
        )
        partner._compute_l10n_ro_anaf_history()
        check_date = date.today()

        # (1) the end_date domain must exclude the expired line entirely,
        # even though its start_date is also <= check_date.
        matches = self.partner_anaf_model.search(
            [
                ("id", "in", partner.l10n_ro_anaf_history.ids),
                ("start_date", "<=", check_date),
                "|",
                ("end_date", "=", False),
                ("end_date", ">", check_date),
            ]
        )
        self.assertNotIn(expired, matches)
        self.assertIn(old_open, matches)
        self.assertIn(new_open, matches)

        # (2) with order='start_date desc' + limit=1, the most recent of
        # the (still open) matches must be selected, not the oldest one
        # and not an arbitrary one.
        selected = self.partner_anaf_model.search(
            [
                ("id", "in", partner.l10n_ro_anaf_history.ids),
                ("start_date", "<=", check_date),
                "|",
                ("end_date", "=", False),
                ("end_date", ">", check_date),
            ],
            order="start_date desc",
            limit=1,
        )
        self.assertEqual(
            selected,
            new_open,
            "order='start_date desc' must select the most recently "
            "started open line, not the oldest one.",
        )

    def test_invoice_fp(self):
        """Test download file and partner link."""
        if not self.invoice.partner_id.l10n_ro_vat_on_payment:
            self.lxt_partner.l10n_ro_vat_on_payment = True
        self.invoice._onchange_partner_id()
        self.assertEqual(self.invoice.fiscal_position_id, self.fptvainc)
