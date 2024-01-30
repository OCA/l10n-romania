import xml.sax
from collections import defaultdict
from datetime import timedelta
from urllib.request import urlopen

from odoo import api, fields, models


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    @api.depends("rate")
    def _compute_invese_rate(self):
        for rec in self:
            rec.inverse_rate = 1 / rec.rate if rec.rate else 1.0

    inverse_rate = fields.Float(
        store=1,
        digits=(16, 4),
        compute=_compute_invese_rate,
        help="Inverse rate computed as 1/rate. If you want to change this, "
        "change the rate ( write =1/desired_inverse_value)",
    )


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

        if date_from == date_to:
            url = "https://www.bnr.ro/nbrfxrates.xml"
        else:
            year = date_from.year
            url = "https://www.bnr.ro/files/xml/years/nbrfxrates" + str(year) + ".xml"

        handler = ROBNRRatesHandler(currencies, date_from, date_to)
        # with urlopen(url, timeout=10) as response:
        #     xml.sax.parse(response, handler)
        response = self.call_bnr(url)
        xml.sax.parseString(response, handler)
        if handler.content:
            return handler.content
        elif date_from == date_to:
            # date_from can be in past and first url is giving only one date
            # we must try to take the date from whole year list
            year = date_from.year
            url = "https://www.bnr.ro/files/xml/years/nbrfxrates" + str(year) + ".xml"
            handler = ROBNRRatesHandler(currencies, date_from, date_to)
            # with urlopen(url, timeout=10) as response:
            #     xml.sax.parse(response, handler)
            response = self.call_bnr(url)
            xml.sax.parseString(response, handler)
        return handler.content or {}

    def call_bnr(self, url):
        """Call BNR and return the response."""
        return urlopen(url, timeout=10).read()


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
