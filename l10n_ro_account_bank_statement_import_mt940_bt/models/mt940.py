# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = "l10n.ro.account.bank.statement.import.mt940.parser"

    def get_header_lines(self):
        if self.get_mt940_type() == "mt940_ro_bt":
            return 1
        return super().get_header_lines()

    def get_header_regex(self):
        if self.get_mt940_type() == "mt940_ro_bt":
            return ":20:"
        return super().get_header_regex()

    def get_tag_61_regex(self):
        if self.get_mt940_type() == "mt940_ro_bt":
            return re.compile(
                r"^(?P<date>\d{6})(?P<line_date>\d{4})(?P<sign>[CD])"
                r"(?P<amount>\d+,\d{2})N(?P<type>.{3})"
                r"(?P<reference>\w+)//(?P<bank_ref>\S+)"
            )
        return super().get_tag_61_regex()

    def handle_tag_28(self, data, result):
        if self.get_mt940_type() == "mt940_ro_bt":
            result["statement"]["name"] = (
                data.replace(".", "").replace("/", "-").strip()
            )
            return result
        return super().handle_tag_28(data, result)

    def handle_tag_61(self, data, result):
        if self.get_mt940_type() != "mt940_ro_bt":
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
            bank_ref = parsed_data.get("bank_ref") or ""
            transaction["ref"] = bank_ref.strip() or parsed_data["reference"]
        return result

    def handle_tag_62F(self, data, result):
        result = super().handle_tag_62F(data, result)
        if (
            self.get_mt940_type() == "mt940_ro_bt"
            and result.get("statement") is not None
        ):
            result["statement"]["_bt_closed"] = True
        return result

    def handle_tag_86(self, data, result):
        if self.get_mt940_type() != "mt940_ro_bt":
            return super().handle_tag_86(data, result)

        if not result["statement"] or not result["statement"]["transactions"]:
            return result
        # The trailing :86: after :62F:/:64: is a summary line (e.g.
        # "Total tranzactii card in asteptare...") and must not overwrite
        # the last transaction.
        if result["statement"].get("_bt_closed"):
            return result

        transaction = result["statement"]["transactions"][-1]
        text = " ".join(line.strip() for line in data.splitlines() if line.strip())
        text = re.sub(r"\s+", " ", text).strip()
        transaction["payment_ref"] = text
        transaction["narration"] = text

        partner_name = self._extract_bt_partner(text)
        if partner_name:
            transaction["partner_name"] = partner_name
            partner = self.env["res.partner"].search(
                [("name", "=ilike", partner_name)], limit=1
            )
            if partner:
                transaction["partner_id"] = partner.id

        return result

    def _extract_bt_partner(self, text):
        """Best-effort extraction of the counterpart name from BT free-text
        tag 86. BT tag 86 is unstructured; we look for common markers."""
        # POS non-BT: "...498750004690344 TID:XXXX <Merchant Name> <country> ..."
        m = re.search(r"TID:\S+\s+(?P<name>.+?)\s+valoare\s+tranzactie", text)
        if m:
            return m.group("name").strip()
        # Interbank transfer typically uses "Beneficiar" / "Ordonator"
        m = re.search(r"(?:Beneficiar|Ordonator)[: ]+(?P<name>[^,/]+)", text)
        if m:
            return m.group("name").strip()
        return False
