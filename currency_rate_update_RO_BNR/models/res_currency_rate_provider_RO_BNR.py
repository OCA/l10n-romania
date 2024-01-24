import xml.sax
from collections import defaultdict
from datetime import timedelta
from urllib.request import urlopen

from odoo import fields, models


class ResCurrencyRateProviderROBNR(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("RO_BNR", "National Bank of Romania")],
        ondelete={"RO_BNR": "set default"},
    )

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

        if date_from == fields.Date.today():
            url = "https://www.bnr.ro/nbrfxrates.xml"
        else:
            year = date_from.year
            url = "http://www.bnr.ro/files/xml/years/nbrfxrates" + str(year) + ".xml"

        handler = ROBNRRatesHandler(currencies, date_from, date_to)
        with urlopen(url, timeout=10) as response:
            xml.sax.parse(response, handler)
        if handler.content:
            return handler.content
        elif date_from == date_to:
            # date_from can be in past and first url is giving only one date
            # we must try to take the date from whole year list
            year = date_from.year
            url = "http://www.bnr.ro/files/xml/years/nbrfxrates" + str(year) + ".xml"
            handler = ROBNRRatesHandler(currencies, date_from, date_to)
            with urlopen(url, timeout=10) as response:
                xml.sax.parse(response, handler)
        return handler.content or {}

    def _update(self, date_from, date_to, newest_only=False):
        # we must take all the years if we have a range of years
        # so, please be carefull since it will fetch rates from begining
        # of the year from date_from date until the end of the year
        # of the date_to date
        res = super()._update(date_from, date_to, newest_only)
        ro_bnr_service = self.filtered(lambda p: p.service == "RO_BNR")
        if ro_bnr_service:
            if date_from and date_to and date_from.year != date_to.year:
                # if we have a range of years we must take all the years
                # not only the date_from year
                for year in range(date_from.year + 1, date_to.year):
                    year_date_from = fields.Date.from_string(str(year) + "-01-01")
                    year_date_to = fields.Date.from_string(str(year) + "-12-31")
                    ro_bnr_service._update(
                        year_date_from, year_date_to, newest_only=False
                    )
        return res


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
            self.multiplier = float(attrs.get("multiplier", 1))
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
