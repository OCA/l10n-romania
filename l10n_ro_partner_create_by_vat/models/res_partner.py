# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CEDILLATRANS = bytes.maketrans(u'\u015f\u0163\u015e\u0162'.encode(
    'utf8'), u'\u0219\u021b\u0218\u021a'.encode('utf8'))

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; MSIE 7.01; Windows NT 5.0)",
    "Content-Type": "application/json;"
}

ANAF_URL = 'https://webservicesp.anaf.ro/PlatitorTvaRest/api/v3/ws/tva'


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    vat_subjected = fields.Boolean('VAT Legal Statement')

    @api.model
    def _get_Anaf(self, cod, data=False):
        # Function to get datas from ANAF Webservice
        # cod = vat number without country code
        # data = date of the interogation
        if not data:
            data = fields.Date.today()
        res = requests.post(ANAF_URL, json=[{'cui': cod, 'data': data}],
                            headers=headers)
        result = {}
        if res.status_code == 200:
            res = res.json()
            if res['found'] and res['found'][0]:
                result = res['found'][0]
        return result

    @api.model
    def _Anaf_to_Odoo(self, result):
        res = {'name': result['denumire'].upper(),
               'vat_subjected': result['scpTVA'],
               'company_type': 'company'}
        addr = city = ''
        if result['adresa']:
            lines = [x for x in result['adresa'].replace(
                'NR,', 'NR.').split(",") if x]
            nostreet = True
            strlistabr = ['STR.', 'ALEEA', 'CAL.', 'INTR.', 'BD-UL']
            for line in lines:
                if any([x in line for x in strlistabr]):
                    nostreet = False
                    break
            if nostreet:
                addr = 'Principala '
            for line in lines:
                line = line.encode('utf8').translate(
                    CEDILLATRANS).decode('utf8')
                if 'JUD.' in line:
                    state = self.env['res.country.state'].search(
                        [('name',
                          '=',
                          line.replace('JUD.', '').strip().title())])
                    if state:
                        res['state_id'] = state[0].id
                elif 'MUN.' in line:
                    city = line.replace('MUN.', '').strip().title()
                elif 'ORȘ.' in line:
                    city = line.replace('ORȘ.', '').strip().title()
                elif 'COM.' in line:
                    city += ' ' + line.strip().title()
                elif ' SAT ' in line:
                    city += ' ' + line.strip().title()
                else:
                    addr += line.replace('STR.', '').strip().title() + ' '
            if city:
                res['city'] = city.replace('-', ' ').title().strip()
        res['street'] = addr.strip()
        return res

    @api.onchange('vat')
    def vies_vat_change(self):
        for partner in self:
            if not partner.vat:
                return {}
            res = {}
            vat = partner.vat.strip().upper()
            vat_country, vat_number = partner._split_vat(vat)
            try:
                if vat_country == 'ro':
                    try:
                        result = partner._get_Anaf(vat_number)
                        if result:
                            res = partner._Anaf_to_Odoo(result)
                    except:
                        _logger.info("ANAF Webservice not working.")
                    if res:
                        res['country_id'] = self.env['res.country'].search(
                            [('code', 'ilike', vat_country)])[0].id
                        partner.update(res)
            except:
                super(ResPartner, partner).vies_vat_change()
