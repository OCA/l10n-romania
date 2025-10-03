# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from unittest.mock import Mock, patch

import requests

from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPartnerVATSubjected(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.mainpartner = cls.env.ref("base.main_partner")
        cls.env.company.l10n_ro_accounting = True


@tagged("post_install", "-at_install")
class TestPartnerVAT(TestPartnerVATSubjected):
    def test_onchange_l10n_ro_vat_subjected(self):
        """Check onchange vat subjected and country."""

        def post(url, **kwargs):
            response = Mock()
            response.status_code = 200
            response._content = b"ok"
            return response

        with mute_logger("odoo.tests.form.onchange"):
            with (
                patch.object(requests, "post", post),
                patch.object(requests.Session, "post", post),
            ):
                # test setting l10n_ro_vat_subjected as True
                partner = self.env["res.partner"].create(
                    {
                        "name": "Test Partner",
                        "is_company": True,
                    }
                )
                partner_form = Form(partner)
                partner_form.vat = "4264242"
                partner_form.country_id = self.env.ref("base.ro")
                partner_form.l10n_ro_vat_subjected = True
                partner_form.save()
                self.assertEqual(partner.vat, "RO4264242")
                # Test setting l10n_ro_vat_subjected as False
                partner_form.l10n_ro_vat_subjected = False
                partner_form.save()
                self.assertEqual(partner.vat, "4264242")
                # Check split vat with no country code in vat
                vat_country, l10n_ro_vat_number = partner._split_vat(partner.vat)
                self.assertEqual(vat_country, "RO")
                self.assertEqual(l10n_ro_vat_number, "4264242")

    def test_form_partner(self):
        test_company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "is_company": True,
            }
        )

        partner_form = Form(partner)
        partner_form.name = "Test Partner"
        partner_form.l10n_ro_vat_subjected = True

        partner_form = Form(partner.with_company(test_company))
        partner_form.name = "Test Partner"
        with self.assertRaises(AssertionError):
            partner_form.l10n_ro_vat_subjected = True
