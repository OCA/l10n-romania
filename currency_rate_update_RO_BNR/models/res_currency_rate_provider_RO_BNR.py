# Copyright 2018 Forest and Biomass Romania
# Copyright 2020 OdooERP Romania SRL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import xml.sax
from collections import defaultdict
from datetime import timedelta
from urllib.request import urlopen

from odoo import fields, models


class ResCurrencyRateProviderROBNR(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(selection_add=[("RO_BNR", "National Bank of Romania")])

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "RO_BNR":
            return super()._get_supported_currencies()  # pragma: no cover
        return [
            "AED",
            "AUD",
            "BGN",
            "BRL",
            "CAD",
            "CHF",
            "CNY",
            "CZK",
            "DKK",
            "EGP",
            "EUR",
            "GBP",
            "HUF",
            "INR",
            "JPY",
            "KRW",
            "MDL",
            "MXN",
            "NOK",
            "NZD",
            "PLN",
            "RON",
            "RSD",
            "RUB",
            "SEK",
            "TRY",
            "UAH",
            "USD",
            "XAU",
            "XDR",
            "ZAR",
        ]

    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()
        if self.service != "RO_BNR":
            return super()._obtain_rates(
                base_currency, currencies, date_from, date_to
            )  # pragma: no cover

        url = "https://www.bnr.ro/nbrfxrates.xml"

        handler = ROBNRRatesHandler(currencies, date_from, date_to)
        with urlopen(url) as response:
            xml.sax.parse(response, handler)
        return handler.content


class ROBNRRatesHandler(xml.sax.ContentHandler):
    def __init__(self, currencies, date_from, date_to):
        self.currencies = currencies
        self.date_from = date_from
        self.date_to = date_to
        self.content = defaultdict(dict)
        self.tags = list()
        self.currency = None
        self.date = None
        self.multiplier = None
        self.rate = None

    def startElement(self, name, attrs):
        if name == "Cube" and "date" in attrs:
            rate_date = fields.Date.from_string(attrs["date"])
            self.date = rate_date + timedelta(days=1)
            self.rates = dict()
        elif name == "Rate" and all([x in attrs for x in ["currency"]]):
            currency = attrs["currency"]
            self.currency = currency
            self.multiplier = attrs.get("multiplier", 1)
            self.rate = 1
        self.tags.append(name)

    def endElement(self, name):
        if name == "Rate":
            if (
                (self.date_from is None or self.date >= self.date_from)
                and (self.date_to is None or self.date <= self.date_to)
                and self.currency in self.currencies
            ):
                self.content[self.date.isoformat()][self.currency] = 1 / (
                    self.rate / self.multiplier
                )
            self.currency = None
            self.rate = None
            self.multiplier = 1
        self.tags.pop()

    def characters(self, content):
        name = self.tags[-1] if len(self.tags) >= 1 else None
        if name == "Rate":
            self.rate = float(content)
