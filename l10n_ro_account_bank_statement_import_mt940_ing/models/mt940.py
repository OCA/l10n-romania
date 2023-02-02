# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = "l10n.ro.account.bank.statement.import.mt940.parser"

    def get_tag_61_regex(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return re.compile(
                r"^(?P<date>\d{6})(?P<sign>[CD])[CDNR](?P<amount>\d+,\d{2})N(?P<type>.{3})"
                r"(?P<reference>\w{0,16})//(?P<ingid>\w{0,14})-(?P<ingtranscode>\w{0,34})"
            )
        return super().get_tag_61_regex()

    def get_header_lines(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return 1
        return super().get_header_lines()

    def get_header_regex(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return ":20:"
        return super().get_header_regex()

    def get_codewords(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return [
                "20",
                "21",
                "22",
                "23",
                "25",
                "26",
                "27",
                "28",
                "29",
                "31",
                "32",
                "33",
                "60",
                "61",
                "110",
                "NAME ACCOUNT OWNER",
                "IBAN NO",
            ]
        return super().get_codewords()

    def get_subfield_split_text(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return "~"
        return super().get_subfield_split_text()

    def get_counterpart(self, transaction, subfield):
        if self.get_mt940_type() == "mt940_ro_ing":
            if not subfield:
                return  # subfield is empty
            subfield = list(filter(lambda a: a != "", subfield))
            if len(subfield) >= 1 and subfield[0]:
                transaction.update({"partner_name": subfield[0].strip()})
            if len(subfield) >= 2 and subfield[1]:
                transaction.update({"account_number": subfield[1].strip()})
            if (
                len(subfield) >= 3
                and subfield[2]
                and not transaction.get("account_number")
            ):
                transaction.update({"account_number": subfield[2].strip()})
            return transaction
        return super().get_counterpart(transaction, subfield)

    def get_subfields(self, data, codewords):
        if self.get_mt940_type() == "mt940_ro_ing":
            subfields = {}
            current_codeword = None
            data = data.replace("\n", " ")

            # pentru eliminarea spatiilor din codewords (in data)
            data = self._clean_codewords(data, codewords)

            for word in data.split(self.get_subfield_split_text()):
                word = word.strip()
                if not word and not current_codeword:
                    continue

                cw_found = False
                for cw in codewords[:-2]:
                    len_cw = len(cw)
                    if word[:len_cw] == cw:
                        current_codeword = cw
                        subfields[cw] = [word[len_cw:]]
                        cw_found = True
                        break

                if cw_found:
                    continue

                if current_codeword in subfields:
                    len_cw = 0 if not cw_found else len(current_codeword)
                    subfields[current_codeword].append(word[len_cw:])
            return subfields
        return super().get_subfields(data, codewords)

    def handle_common_subfields(self, transaction, subfields):
        """Deal with common functionality for tag 86 subfields."""
        # Get counterpart from 31, 32 or 33 subfields:
        if self.get_mt940_type() == "mt940_ro_ing":
            counterpart_fields = []
            if "110" in subfields:
                # tag 86 nestructurat
                journal = self.env["account.journal"].browse(
                    self._context["journal_id"]
                )
                patterns = journal.bank_account_id.l10n_ro_unstructured_tag86.split(
                    "\n"
                )

                data = "".join(subfields["110"])
                result = None
                for pattern in patterns:
                    pattern = re.compile(pattern)
                    result = pattern.match(data)
                    if result:
                        result = result.groupdict()
                        break

                if result:
                    if result.get("vat"):
                        partner = self.env["res.partner"].search(
                            [("l10n_ro_vat_number", "like", result["vat"])], limit=1
                        )
                        if partner:
                            transaction.update({"partner_id": partner.id})
                    if result.get("partner_name"):
                        transaction.update({"partner_name": result["partner_name"]})
                    if result.get("account_number"):
                        transaction.update({"account_number": result["account_number"]})
            for counterpart_field in [
                "31",
                "32",
                "33",
                "NAME ACCOUNT OWNER",
                "IBAN NO",
            ]:
                if counterpart_field in subfields:
                    if counterpart_field == "31" and counterpart_field in subfields:
                        subfields[counterpart_field][0] = subfields[counterpart_field][
                            0
                        ].replace(" ", "")
                    new_value = subfields[counterpart_field][0].replace("CUI/CNP", "")
                    counterpart_fields.append(new_value)
                else:
                    counterpart_fields.append("")
            if counterpart_fields:
                transaction = self.get_counterpart(transaction, counterpart_fields)
            if not transaction.get("payment_ref"):
                transaction["payment_ref"] = "/"
            for counterpart_field in [
                "20",
                "21",
                "22",
                "23",
                "25",
                "26",
                "27",
                "28",
                "29",
                "60",
                "61",
                "110",
            ]:
                if counterpart_field in subfields:
                    transaction["payment_ref"] += "/".join(
                        x for x in subfields[counterpart_field] if x
                    )
            # Get transaction reference subfield (might vary):
            if transaction.get("ref") in subfields:
                transaction["ref"] = "".join(subfields[transaction["ref"]])
            return transaction
        return super().handle_common_subfields(transaction, subfields)

    def handle_tag_25(self, data, result):
        if self.get_mt940_type() == "mt940_ro_ing":
            result["account_number"] = data.replace("/", "").strip()
            return result
        return super().handle_tag_25(data, result)

    def handle_tag_28(self, data, result):
        """Sequence number within batch - normally only zeroes."""
        if result["statement"] and self.get_mt940_type() == "mt940_ro_ing":
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
        if result["statement"] and self.get_mt940_type() == "mt940_ro_ing":
            result["statement"]["balance_end_real"] = self.parse_amount(
                data[0], data[10:]
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
                is_account_number = statement_name.startswith(result["account_number"])
                if is_account_number and result["statement"]["date"]:
                    result["statement"]["name"] += " - " + result["statement"][
                        "date"
                    ].strftime("%Y-%m-%d")
            return result
        return super().handle_tag_62F(data, result)
