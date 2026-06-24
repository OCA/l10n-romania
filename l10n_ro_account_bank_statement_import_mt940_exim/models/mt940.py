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
                r"(?P<reference>\w+)\s*//\s*(?P<bank_ref>\S+)\s*(?P<info>.*)"
            )
        return super().get_tag_61_regex()

    def handle_tag_28(self, data, result):
        if self.get_mt940_type() == "mt940_ro_exim":
            result["statement"]["name"] = data.replace(".", "").strip()
            return result
        return super().handle_tag_28(data, result)

    def handle_tag_61(self, data, result):
        if self.get_mt940_type() != "mt940_ro_exim":
            return super().handle_tag_61(data, result)

        tag_61_regex = self.get_tag_61_regex()
        re_61 = tag_61_regex.match(data)
        if re_61 and result["statement"] is not None:
            parsed_data = re_61.groupdict()
            result["statement"]["transactions"].append({})
            transaction = result["statement"]["transactions"][-1]
            transaction["date"] = datetime.strptime(parsed_data["date"], "%y%m%d")
            transaction["amount"] = self.parse_amount(
                parsed_data["sign"], parsed_data["amount"]
            )
            bank_ref = (parsed_data.get("bank_ref") or "").strip()
            info = (parsed_data.get("info") or "").strip()
            transaction["ref"] = bank_ref or parsed_data["reference"]
            if info:
                transaction["narration"] = info
        return result

    def handle_tag_86(self, data, result):
        if self.get_mt940_type() != "mt940_ro_exim":
            return super().handle_tag_86(data, result)

        if not result["statement"] or not result["statement"]["transactions"]:
            return result

        transaction = result["statement"]["transactions"][-1]
        text = " ".join(line.strip() for line in data.splitlines() if line.strip())
        text = re.sub(r"\s+", " ", text).strip()

        # Eximbank tag 86 typically starts with "Counterpart:/<description>"
        description = text
        m = re.match(r"^Counterpart:\s*/?\s*(?P<desc>.*)", text)
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
            transaction["partner_name"] = partner_name
            partner = self.env["res.partner"].search(
                [("name", "=ilike", partner_name)], limit=1
            )
            if partner:
                transaction["partner_id"] = partner.id

        return result

    def _extract_exim_partner(self, text):
        """Best-effort extraction of the counterpart name from Eximbank
        tag 86. The text is unstructured Romanian narrative; we look for
        a trailing company suffix (SRL, SA, PFA, etc.)."""
        m = re.search(
            r"(?P<name>[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț\.\- ]+?\s+(?:S\.?\s*R\.?\s*L\.?|S\.?\s*A\.?|PFA|SNC))",  # noqa: E501
            text,
        )
        if m:
            return m.group("name").strip()
        return False
