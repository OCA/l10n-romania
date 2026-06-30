# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = "l10n.ro.account.bank.statement.import.mt940.parser"

    def get_header_lines(self):
        if self.get_mt940_type() == "mt940_ro_exim":
            return 1
        return super().get_header_lines()

    def get_header_regex(self):
        if self.get_mt940_type() == "mt940_ro_exim":
            return ":20:"
        return super().get_header_regex()

    def get_tag_61_regex(self):
        if self.get_mt940_type() == "mt940_ro_exim":
            # Eximbank tag 61 carries an extra funds_code letter (e.g. 'N')
            # between the sign and the amount, plus an optional supplementary
            # code on a continuation line (e.g. CRRD.57482).
            return re.compile(
                r"^(?P<date>\d{6})(?P<line_date>\d{4})(?P<sign>[CD])"
                r"(?P<funds_code>[A-Z])?(?P<amount>\d+,\d{2})N(?P<type>.{3})"
                r"(?P<reference>\w+)\s*//\s*(?P<bank_ref>\d+)\s*(?P<info>.*)"
            )
        return super().get_tag_61_regex()

    def handle_tag_28C(self, data, result):
        if result["statement"] and self.get_mt940_type() == "mt940_ro_exim":
            if result["statement"]["name"]:
                result["statement"]["name"] += " - " + data
            else:
                result["statement"]["name"] = data
        return super().handle_tag_28C(data, result)

    def handle_tag_61(self, data, result):
        if self.get_mt940_type() != "mt940_ro_exim":
            return super().handle_tag_61(data, result)

        tag_61_regex = self.get_tag_61_regex()
        re_61 = tag_61_regex.match(data)
        if re_61 and result["statement"] is not None:
            parsed_data = re_61.groupdict()
            result["statement"]["transactions"].append({})
            transaction = result["statement"]["transactions"][-1]
            transaction["date"] = datetime.strptime(
                parsed_data["date"], "%y%m%d"
            ).date()
            transaction["amount"] = self.parse_amount(
                parsed_data["sign"], parsed_data["amount"]
            )
            bank_ref = (parsed_data.get("bank_ref") or "").strip()
            transaction["ref"] = bank_ref or parsed_data["reference"]
            # info = (parsed_data.get("info") or "").strip()
            # if info:
            #     transaction["narration"] = info
        return result

    def handle_tag_86(self, data, result):
        if self.get_mt940_type() != "mt940_ro_exim":
            return super().handle_tag_86(data, result)

        if not result["statement"] or not result["statement"]["transactions"]:
            return result

        transaction = result["statement"]["transactions"][-1]

        # Collapse any runs of whitespace that survive from the original file
        # (e.g. "NEXTERP   ROMANIA SRL" with 2-3 spaces, into a single space
        # so partner-name and IBAN regexes work consistently.
        data = re.sub(r"\s+", " ", data).strip()

        # Eximbank tag 86 typically starts with "Counterpart:/<description>"
        description = data
        m = re.match(r"^Counterpart:\s*/?\s*(?P<desc>.*)", data)
        if m:
            description = m.group("desc").strip()

        transaction["payment_ref"] = description or "/"
        if transaction.get("narration"):
            transaction["narration"] = (
                description + " - " + transaction["narration"]
            ).strip(" -")
        else:
            transaction["narration"] = description

        partner_name = self._extract_exim_partner(description)
        if partner_name:
            cif = self._extract_exim_partner_cif(data)
            transaction["partner_name"] = partner_name
            domain = [("name", "=ilike", partner_name)]
            if cif:
                domain = ["|", ("vat", "like", cif)] + domain
            partner = self.env["res.partner"].search(domain, limit=1)
            if partner:
                transaction["partner_name"] = partner.name
                transaction["partner_id"] = partner.id

        partner_bank_account = self._extract_exim_partner_bank_account(data)
        if partner_bank_account:
            transaction["account_number"] = partner_bank_account

        return result

    def _extract_exim_partner(self, data):
        """Best-effort extraction of the counterpart name from Eximbank
        tag 86. The data is unstructured Romanian narrative; we look for
        a trailing company suffix (SRL, SA, PFA, etc.)."""
        m = re.search(
            r"(?P<name>[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț\.\- ]+?\s+(?:S\.?\s*R\.?\s*L\.?|S\.?\s*A\.?|PFA|SNC))",  # noqa: E501
            data,
        )
        if m:
            return m.group("name").strip()
        return False

    def _extract_exim_partner_cif(self, data):
        # Structured format: /PARTNER NAME/CIF / — CIF is 5–9 digits followed by
        # a space and then a slash, which distinguishes it from OP references
        # that are longer (16 digits) or separated by double-slash (//).
        m = re.search(r"/(\d{5,9})\s+/", data)
        if m:
            return m.group(1)
        return False

    def _extract_exim_partner_bank_account(self, data):
        # Eximbank places the counterpart IBAN directly after "Counterpart:"
        # e.g. "Counterpart:RO32BRDE130SV65403551300/Incasare OP/..."
        m = re.match(r"Counterpart:\s*([A-Z]{2}\d{2}[A-Z0-9]{4,30})/", data)
        if m:
            return m.group(1)
        return False
