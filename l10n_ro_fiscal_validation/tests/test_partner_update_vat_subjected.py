# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import codecs
import csv
import os
from unittest.mock import Mock, patch

import requests

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


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
        for line in lines:
            cls.partner_model.with_context(**context).create(
                {
                    "id": line["id"],
                    "name": line["name"],
                    "vat": line["vat"],
                    "is_company": line["is_company"],
                    "country_id": cls.env.ref("base.ro").id,
                }
            )


class TestUpdatePartner(TestPartnerUpdateVatSubjectedBase):
    def test_vat_subjected_cron(self):
        """Check methods vat from ANAF."""

        def post(url, **kwargs):
            response = Mock()
            response.status_code = 200
            response._content = b"ok"
            return response

        with mute_logger("odoo.addons.l10n_ro_fiscal_validation.models.res_partner"):
            with (
                patch.object(requests, "post", post),
                patch.object(requests.Session, "post", post),
            ):
                self.partner_model._update_l10n_ro_vat_subjected_all()
