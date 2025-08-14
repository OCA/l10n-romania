# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = "l10n.ro.account.bank.statement.import.mt940.parser"

    def pre_process_data(self, data):
        if self.get_mt940_type() == "mt940_ro_alpha":
            data = data.replace(data[:55], "")
        return super().pre_process_data(data)

    def get_tag_61_regex(self):
        if self.get_mt940_type() == "mt940_ro_alpha":
            return re.compile(
                r"^(?P<date>\d{6})(?P<line_date>\d{0,4})"
                r"(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})"
                r"(?P<reference>\w{1,50})"
            )
        return super().get_tag_61_regex()

    def get_header_lines(self):
        if self.env.context.get("type") == "mt940_ro_alpha":
            return 1
        return super().get_header_lines()

    def get_header_regex(self):
        if self.get_mt940_type() == "mt940_ro_alpha":
            return "{4:"
        return super().get_header_regex()

    def get_footer_regex(self):
        if self.get_mt940_type() == "mt940_ro_alpha":
            return "\r\n-}"
        return super().get_footer_regex()

    def get_subfield_split_text(self):
        if self.get_mt940_type() == "mt940_ro_alpha":
            return " "
        return super().get_subfield_split_text()

    def get_codewords(self):
        if self.get_mt940_type() == "mt940_ro_alpha":
            return ["BENEFICIAR", "PLATITOR", "DETALII", "CUST"]
        return super().get_codewords()

    def handle_tag_25(self, data, result):
        if self.get_mt940_type() == "mt940_ro_alpha":
            data = data.replace(".", "").strip()[:21]
            result["account_number"] = data
            return result
        return super().handle_tag_25(data, result)

    def handle_tag_28(self, data, result):
        """Sequence number within batch - normally only zeroes."""
        if result["statement"] and self.get_mt940_type() == "mt940_ro_alpha":
            if result["statement"]["name"]:
                result["statement"]["name"] += data.replace(".", "").strip()
            else:
                result["statement"]["name"] = data
            return result
        return super().handle_tag_28(data, result)

    def handle_tag_62F(self, data, result):
        """Get ending balance, statement date and id.

        We use the date on the last 62F tag as statement date, as the date
        on the 60F record (previous end balance) might contain a date in
        a previous period.

        We generate the statement.id from the local_account and the end-date,
        this should normally be unique, provided there is a maximum of
        one statement per day.

        Depending on the bank, there might be multiple 62F tags in the import
        file. The last one counts.
        """
        if self.get_mt940_type() == "mt940_ro_alpha":
            if result["statement"]:
                amount = data[10:]
                end_amount_reg = re.compile(r"^(?P<amount>\d+,\d{2})")
                re_amount = end_amount_reg.match(data[10:]).groupdict()
                if re_amount:
                    amount = re_amount.get("amount")
                result["statement"]["balance_end_real"] = self.parse_amount(
                    data[0], amount
                )
                result["statement"]["date"] = datetime.strptime(data[1:7], "%y%m%d")

                # Only replace logically empty (only whitespace or zeroes) id's:
                # But do replace statement_id's added before (therefore starting
                # with local_account), because we need the date on the last 62F
                # record.
                statement_name = result["statement"]["name"] or ""
                if result["statement"]["name"] is None and result["account_number"]:
                    result["statement"]["name"] = result["account_number"]
                if statement_name:
                    is_account_number = statement_name.startswith(
                        result["account_number"]
                    )
                    if is_account_number and result["statement"]["date"]:
                        result["statement"]["name"] += " - " + result["statement"][
                            "date"
                        ].strftime("%Y-%m-%d")
            return result
        return super().handle_tag_62F(data, result)

    def handle_tag_86(self, data, result):
        if self.env.context.get("type") == "mt940_ro_alpha":
            transaction = {}
            if result["statement"]["transactions"]:
                transaction = result["statement"]["transactions"][-1]
            if not transaction.get("payment_ref", False):
                transaction["payment_ref"] = data
                transaction["narration"] = data
                regec_p = r".*PLATITOR(?P<platitor>.*)(?P<iban_p>\w{24})"
                regec_b = r".*BENEFICIAR(?P<beneficiar>.*)(?P<iban_b>\w{24})"
                regec_d = r".*DETALII(?P<detalii>.*)"
                regec_ref = r".*CUST REFERENCE(?P<ref>.*)"

                tag_86_regex_v1 = re.compile(regec_p + regec_b + regec_d + regec_ref)
                tag_86_regex_v2 = re.compile(regec_b + regec_p + regec_d + regec_ref)
                tag_86_regex_v3 = re.compile(regec_p + regec_d + regec_ref)
                tag_86_regex_v4 = re.compile(regec_b + regec_d + regec_ref)

                re_86 = tag_86_regex_v1.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v2.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v3.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v4.match(data)
                if re_86:
                    parsed_data = re_86.groupdict()
                    if transaction["amount"] > 0:
                        transaction["partner_name"] = parsed_data.get(
                            "platitor", ""
                        ).strip()
                        transaction["account_number"] = parsed_data.get("iban_p")

                    else:
                        transaction["partner_name"] = parsed_data.get(
                            "beneficiar", ""
                        ).strip()
                        transaction["account_number"] = parsed_data.get("iban_b")

                    if parsed_data.get("detalii"):
                        transaction["payment_ref"] = parsed_data.get("detalii")

                    transaction["ref"] = parsed_data.get("ref")
            return result
        return super().handle_tag_86(data, result)
