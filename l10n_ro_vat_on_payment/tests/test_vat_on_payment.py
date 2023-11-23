# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
import shutil
from datetime import date, timedelta

import requests

from odoo import tools
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestVATonpayment(AccountTestInvoicingCommon):
    """Run test for VAT on payment."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super().setUpClass(chart_template_ref=ro_template_ref)
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
        cls.fptvainc = cls.fp_model.search(
            [
                ("name", "ilike", "Regim TVA la Incasare"),
                ("company_id", "=", cls.env.company.id),
            ]
        )
        data_dir = tools.config["data_dir"]
        istoric_file = os.path.join(data_dir, "istoric.txt")

        test_file = get_module_resource(
            "l10n_ro_vat_on_payment", "tests", "istoric.txt"
        )
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

    def test_invoice_fp(self):
        """Test download file and partner link."""
        if not self.invoice.partner_id.l10n_ro_vat_on_payment:
            self.lxt_partner.l10n_ro_vat_on_payment = True
        self.invoice._onchange_partner_id()
        self.assertEqual(self.invoice.fiscal_position_id, self.fptvainc)
