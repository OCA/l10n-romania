# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import codecs
import copy
import csv
import os
from unittest.mock import patch

import requests

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_ro_partner_create_by_vat.tests.anaf_data import ANAF_TEST_DATA


class TestPartnerUpdateVatSubjectedBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        parts = cls.partner_model.search(
            [("country_id", "=", cls.env.ref("base.ro").id)]
        )
        parts.write({"country_id": False})
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples/"
        )
        context = {
            "tracking_disable": True,
            "no_vat_validation": True,
        }

        f = open(os.path.join(data_dir, "res.partner.csv"), "rb")

        csvdata = csv.DictReader(codecs.iterdecode(f, "utf-8"))

        lines = [line for line in csvdata if any(line)]
        cls.env.user.company_id.write({"vat_check_vies": False})
        # A single create() for the whole file: the cron is checked against
        # more than one ANAF chunk, so this builds over a thousand partners.
        cls.partners = cls.partner_model.with_context(**context).create(
            [
                {
                    "name": line["name"],
                    "vat": line["vat"],
                    "is_company": line["is_company"],
                    "country_id": cls.env.ref("base.ro").id,
                }
                for line in lines
            ]
        )


class TestUpdatePartner(TestPartnerUpdateVatSubjectedBase):
    def test_vat_subjected_cron(self):
        """The cron asks ANAF about every Romanian company and writes back."""
        # The company the fake ANAF will answer about.
        partner = self.partners[0]
        cui = int(partner.l10n_ro_vat_number)
        answer = copy.deepcopy(ANAF_TEST_DATA["4264242"])
        answer["date_generale"]["cui"] = cui
        answer["date_generale"]["denumire"] = "PARTENER VERIFICAT ANAF SRL"
        answer["inregistrare_scop_Tva"]["scpTVA"] = True

        calls = []

        class FakeResponse:
            """Answers without a correlationId, so the cron stays on the direct
            path: no polling sleep and no follow-up request."""

            status_code = 200

            def json(self):
                return {"found": [answer], "notFound": []}

        def post(url, **kwargs):
            calls.append(kwargs.get("json"))
            return FakeResponse()

        with mute_logger("odoo.addons.l10n_ro_fiscal_validation.models.res_partner"):
            with (
                patch.object(requests, "post", post),
                patch.object(requests.Session, "post", post),
            ):
                self.partner_model._update_l10n_ro_vat_subjected_all()

        self.assertTrue(calls, "the cron must call ANAF")
        self.assertGreater(
            len(calls), 1, "more than a thousand partners must be sent in chunks"
        )
        asked = {item["cui"] for chunk in calls for item in chunk}
        self.assertIn(cui, asked, "the partner must be part of what is asked of ANAF")
        self.assertEqual(partner.name, "PARTENER VERIFICAT ANAF SRL")
        self.assertTrue(partner.l10n_ro_vat_subjected)
