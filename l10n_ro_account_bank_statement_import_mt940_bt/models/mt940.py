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

    def add_record_line(self, line, record_line):
        if self.get_mt940_type() == "mt940_ro_bt":
            # The base parser concatenates continuation lines with no separator.
            # Strip each line's leading/trailing whitespace and join with a single
            # space so that word boundaries at line breaks are preserved (e.g.
            # "WORK UP\n CONSULTING" → "WORK UP CONSULTING").
            return (record_line + " " + line.strip()) if record_line else line
        return super().add_record_line(line, record_line)

    def handle_tag_28C(self, data, result):
        """Sequence number within batch - normally only zeroes."""
        if result["statement"] and self.get_mt940_type() == "mt940_ro_bt":
            if result["statement"]["name"]:
                result["statement"]["name"] += " - " + data
            else:
                result["statement"]["name"] = data
            return result
        return super().handle_tag_28C(data, result)

    def handle_tag_61(self, data, result):
        if self.get_mt940_type() != "mt940_ro_bt":
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
            bank_ref = parsed_data.get("bank_ref") or ""
            transaction["ref"] = bank_ref.strip() or parsed_data["reference"]
        return result

    def handle_tag_62F(self, data, result):
        result = super().handle_tag_62F(data, result)
        if self.get_mt940_type() == "mt940_ro_bt":
            result["_bt_closed"] = True
        return result

    def handle_tag_86(self, data, result):
        if self.get_mt940_type() != "mt940_ro_bt":
            return super().handle_tag_86(data, result)

        if not result["statement"] or not result["statement"]["transactions"]:
            return result
        # The trailing :86: after :62F:/:64: is a summary line (e.g.
        # "Total tranzactii card in asteptare...") and must not overwrite
        # the last transaction.
        if result.get("_bt_closed"):
            return result

        transaction = result["statement"]["transactions"][-1]

        # Collapse any runs of whitespace that survive from the original file
        # (e.g. "CONSULTING   MARKETING" with 3 spaces, or "BTRLRO22  REF:" with 2)
        # into a single space so partner-name and IBAN regexes work consistently.
        data = re.sub(r"\s+", " ", data).strip()
        if not transaction.get("payment_ref", ""):
            transaction["payment_ref"] = data
        transaction["narration"] = data

        # Fallback for transactions without CIF (e.g. Plata OP / debit)
        partner_name = self._extract_bt_partner(data)
        if partner_name:
            cif = self._extract_bt_partner_cif(data)
            transaction["partner_name"] = partner_name
            domain = [("name", "=ilike", partner_name)]
            if cif:
                domain = ["|", ("vat", "like", cif)] + domain
            partner = self.env["res.partner"].search(domain, limit=1)
            if partner:
                transaction["partner_name"] = partner.name
                transaction["partner_id"] = partner.id
        partner_bank_account = self._extract_bt_partner_bank_account(data)
        if partner_bank_account:
            transaction["account_number"] = partner_bank_account
        return result

    def _extract_bt_partner(self, data):
        """Best-effort extraction of the counterpart name from BT free-text
        tag 86. BT tag 86 is unstructured; we look for common markers."""
        # OP / Instant transfers: partner name always immediately precedes the IBAN.
        # Strategy: match the shortest sequence of "uppercase words" before RO<IBAN>.
        #   - First word: [A-Z]{2}... (two consecutive uppercase letters) — rejects
        #     alphanumeric reference tokens like "K2D3R5" or a lone trailing letter.
        #   - Subsequent words: [A-Z]... — allows abbreviations like "S R L", "D".
        #   - Each word may contain digits, hyphens, apostrophes, dots (e.g. S.R.L.).
        #   - Non-greedy *? stops at the FIRST IBAN, so BIC codes after the IBAN are
        #     never included in the name.
        #   - Digit-only tokens (018694, 115, 24 …) start with [0-9] so they break the
        #     word chain, preventing reference numbers from leaking into the name.
        m = re.search(
            r"(?P<name>[A-Z]{2}[A-Z0-9.\-']*(?:\s+[A-Z][A-Z0-9.\-']*)*?)\s+RO\d{2}[A-Z]{4}",
            data,
        )
        if m:
            return m.group("name").strip()
        # Internal transfer: "Alimentare cont PARTNER NAME REF:"
        m = re.search(r"Alimentare cont\s+(?P<name>.+?)\s+REF:", data, re.IGNORECASE)
        if m:
            return m.group("name").strip()
        # POS non-BT: "...498750004690344 TID:XXXX <Merchant Name> <country> ..."
        m = re.search(r"TID:\S+\s+(?P<name>.+?)\s+valoare\s+tranzactie", data)
        if m:
            return m.group("name").strip()
        # Interbank transfer typically uses "Beneficiar" / "Ordonator"
        m = re.search(r"(?:Beneficiar|Ordonator)[: ]+(?P<name>[^,/]+)", data)
        if m:
            return m.group("name").strip()
        return False

    def _extract_bt_partner_cif(self, data):
        m = re.search(r"C\.I\.F\.?:?\s*(?P<cif>\d{5,})", data)
        if m:
            return m.group("cif").strip()
        return False

    def _extract_bt_partner_bank_account(self, data):
        m = re.search(r"(?P<iban>[A-Z]{2}\d{2}[A-Z0-9]{10,30})", data)
        if m:
            return m.group("iban").strip()
        return False
