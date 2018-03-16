# Copyright (C) 2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
import requests
from requests.adapters import HTTPAdapter

from odoo import api, fields, models

CEDILLATRANS = bytes.maketrans(u'\u015f\u0163\u015e\u0162'.encode(
    'utf8'), u'\u0219\u021b\u0218\u021a'.encode('utf8'))

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8"
}

ANAF_BULK_URL = 'https://webservicesp.anaf.ro/AsynchWebService/api/v3/ws/tva'
ANAF_CORR = 'https://webservicesp.anaf.ro/AsynchWebService/api/v3/ws/tva?id=%s'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def update_vat_subjected(self):
        s = request.Session()
        s.mount('https', HTTPAdapter(max_retries=3))
        anaf_dict = []
        check_date = fields.Date.today()
        # Build list of vat numbers to be checked on ANAF
        for partner in self:
            anaf_dict.append(partner.vat_number)
        chunk = []
        chunks = []
        # Process 500 vat numbers once
        max_no = 499
        for position in range(0, len(anaf_dict), max_no):
            chunk = anaf_dict[position:position+max_no]
            chunks.append(chunk)
        for chunk in chunks:
            anaf_ask = []
            for item in chunk:
                anaf_ask.append({'cui': int(item), 'data': check_date})
            res = s.post(
                ANAF_BULK_URL,
                json=anaf_ask,
                headers=headers)
            if res.raise_for_status():
                res = res.json()
                if res['correlationId']:
                    time.sleep(3)
                    resp = s.get(ANAF_CORR % res['correlationId'])
                    if resp.raise_for_status():
                        resp = resp.json()
                        for res in resp['found'] + resp['notfound']:
                            partner = self.search(
                                [('vat_number', '=', res['cui'])])
                            if partner:
                                data = partner._Anaf_to_Odoo(res)
                                partner.update(data)
            time.sleep(2)

    @api.multi
    def update_vat_subjected_all(self):
        partners = self.search(
            [('vat', '!=', False),
             ('country_id', '=', self.env.ref('base.ro').id),
             ('is_company', '=', True)])
        partners.update_vat_subjected()

    @api.model
    def _update_vat_subjected_all(self):
        self.update_vat_subjected_all()
