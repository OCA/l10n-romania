# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import os

from odoo import tools
from odoo.tests import common
from odoo.tools import pycompat


class TestPartnerUpdateVatSubjectedBase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPartnerUpdateVatSubjectedBase, cls).setUpClass()
        cls.partner_model = cls.env["res.partner"]
        parts = cls.partner_model.search(
            [("country_id", "=", cls.env.ref("base.ro").id)]
        )
        parts.write({"country_id": False})
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples/"
        )
        context = {"tracking_disable": True}
        fdata = tools.file_open(data_dir + "res.partner.csv")
        csvdata = pycompat.csv_reader(
            io.BytesIO(bytes(fdata.read(), "utf-8")), quotechar='"', delimiter=","
        )
        lines = [line for line in csvdata if any(line)]
        cls.env.user.company_id.write({"vat_check_vies": False})
        for line in lines:
            cls.partner_model.with_context(context).create(
                {
                    "id": line[0],
                    "name": line[1],
                    "vat": line[2],
                    "is_company": line[3],
                    "country_id": cls.env.ref("base.ro").id,
                }
            )


class TestUpdatePartner(TestPartnerUpdateVatSubjectedBase):
    def test_vat_subjected_cron(self):
        """Check methods vat from ANAF."""
        # Test cron update vat subjected from ANAF
        self.partner_model._update_l10n_ro_vat_subjected_all()
