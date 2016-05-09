# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

import requests

from string import maketrans
from lxml import html

from openerp import models, api

CEDILLATRANS = maketrans(u'\u015f\u0163\u015e\u0162'.encode(
    'utf8'), u'\u0219\u021b\u0218\u021a'.encode('utf8'))

headers = {
    "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)",
    "Content-Type": "multipart/form-data;"
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_Mfinante(self, cod):
        params = {'cod': cod}
        res = requests.get(
            'http://www.mfinante.ro/infocodfiscal.html',
            params=params,
            headers=headers
        )
        res.raise_for_status()

        htm = html.fromstring(res.text)
        # There are 2 table, the first one contains partner datas.
        table = htm.xpath("//div[@id='main']//center/table")[0]
        result = dict()
        for tr in table.iterchildren():
            key = ' '.join([x.strip() for x in tr.getchildren()[
                           0].text_content().split('\n') if x.strip() != ''])
            val = ' '.join([x.strip() for x in tr.getchildren()[
                           1].text_content().split('\n') if x.strip() != ''])
            result[key] = val.encode('utf8').translate(
                CEDILLATRANS).decode('utf8')
        return result

    @api.model
    def _Mfinante_to_Odoo(self, result):
        res = {}
        nrc_key = 'Numar de inmatriculare la Registrul Comertului:'
        tva_key = 'Taxa pe valoarea adaugata (data luarii in evidenta):'
        if 'Denumire platitor:' in result.keys():
            res['name'] = result['Denumire platitor:']
        if 'Adresa:' in result.keys():
            res['street'] = result['Adresa:'].strip().title()
        if nrc_key in result.keys():
            nrc = result[nrc_key].strip()
            if nrc == '-/-/-':
                nrc = ''
            res['nrc'] = nrc
        if 'Codul postal:' in result.keys():
            res['zip'] = result['Codul postal:'] or ''
        if 'Judetul:' in result.keys():
            jud = result['Judetul:'].title() or ''
            state = False
            if jud.lower().startswith('municip'):
                jud = ' '.join(jud.split(' ')[1:]).strip()
                if jud != '':
                    state = self.env['res.country.state'].search(
                        [('name', 'ilike', jud)])
                    if state:
                        state = state[0].id
            res['state_id'] = state
        if 'Telefon:' in result.keys():
            res['phone'] = result['Telefon:'].replace('.', '') or ''
        if 'Fax:' in result.keys():
            res['fax'] = result['Fax:'].replace('.', '') or ''
        if tva_key in result.keys():
            res['vat_subjected'] = bool(result[tva_key] != 'NU')
        return res

    @api.model
    def _get_Openapi(self, cod):
        result = requests.get('http://openapi.ro/api/companies/%s.json' %
                              cod)
        return result

    @api.model
    def _Openapi_to_Odoo(self, result):
        res = {}
        result = result.json()
        state = False
        if res.get('state'):
            state = self.env['res.country.state'].search(
                [('name', '=', res.get('state').title())])
            if state:
                state = state[0].id
        res['name'] = res.get('name')
        res['nrc'] = res.get('registration_id')
        res['street'] = res.get('address')
        res['city'] = res.get('city')
        res['state_id'] = state
        res['phone'] = res.get('phone')
        res['fax'] = res.get('fax')
        res['zip'] = res.get('zip')
        res['vat_subjected'] = bool(res.get('vat', '0') == '1')
        return res

    @api.model
    def _get_partner_data(self, vat):
        vat = vat.strip().upper()
        vat_country, vat_number = self._split_vat(vat)
        if vat_country == 'ro':
            result = self._get_Mfinante(vat_number)
            if result:
                res = self._Mfinante_to_Odoo(result)
            else:
                result = self._get_Openapi(vat_number)
                if result.status_code == 200:
                    res = self._Openapi_to_Odoo(result)
            res['country_id'] = self.env['res.country'].search(
                [('code', 'ilike', vat_country)])[0].id
            return res
        else:
            super(ResPartner, self)._get_partner_data()
