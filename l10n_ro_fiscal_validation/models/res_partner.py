# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time

import requests

from odoo import api, fields, models

CEDILLATRANS = bytes.maketrans(
    u"\u015f\u0163\u015e\u0162".encode("utf8"),
    u"\u0219\u021b\u0218\u021a".encode("utf8"),
)

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;",
}

ANAF_BULK_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v6/ws/tva"
ANAF_CORR = "https://webservicesp.anaf.ro/AsynchWebService/api/v6/ws/tva?id=%s"


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def update_vat_subjected(self):
        anaf_dict = []
        check_date = fields.Date.to_string(fields.Date.today())
        # Build list of vat numbers to be checked on ANAF
        for partner in self:
            anaf_dict.append(partner.vat_number)
        chunk = []
        chunks = []
        # Process 500 vat numbers once
        max_no = 499
        for position in range(0, len(anaf_dict), max_no):
            chunk = anaf_dict[position : position + max_no]
            chunks.append(chunk)
        for chunk in chunks:
            anaf_ask = []
            for item in chunk:
                anaf_ask.append({"cui": int(item), "data": check_date})
            res = requests.post(ANAF_BULK_URL, json=anaf_ask, headers=headers)
            if res.status_code == 200:
                res = res.json()
                if res["correlationId"]:
                    time.sleep(3)
                    resp = requests.get(ANAF_CORR % res["correlationId"])
                    if resp.status_code == 200:
                        resp = resp.json()
                        for res in resp["found"] + resp["notfound"]:
                            partners = self.search(
                                [
                                    ("vat_number", "=", res["cui"]),
                                    ("is_company", "=", True),
                                ]
                            )
                            for partner in partners:
                                data = partner._Anaf_to_Odoo(res)
                                partner.update(data)

    @api.model
    def update_vat_subjected_all(self):
        partners = self.search(
            [
                ("vat", "!=", False),
                ("country_id", "=", self.env.ref("base.ro").id),
                ("is_company", "=", True),
            ]
        )
        partners.update_vat_subjected()

    @api.model
    def _update_vat_subjected_all(self):
        self.update_vat_subjected_all()
