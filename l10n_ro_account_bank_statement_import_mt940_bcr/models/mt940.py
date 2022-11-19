# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)


class MT940Parser(models.AbstractModel):
    _inherit = "l10n.ro.account.bank.statement.import.mt940.parser"

    def get_header_lines(self):
        if self.env.context.get("type") == "mt940_ro_bcr":
            return 1
        return super().get_header_lines()

    def get_header_regex(self):
        if self.env.context.get("type") == "mt940_ro_bcr":
            return ":20:"
        return super().get_header_regex()

    def get_subfield_split_text(self):
        if self.env.context.get("type") == "mt940_ro_bcr":
            return "-"
        return super().get_subfield_split_text()

    def get_codewords(self):
        if self.env.context.get("type") == "mt940_ro_bcr":
            return ["Referinta", "Platitor", "Beneficiar", "Detalii", "CODFISC"]
        return super().get_codewords()

    def get_tag_61_regex(self):
        if self.env.context.get("type") == "mt940_ro_bcr":
            return re.compile(
                r"(?P<date>\d{6})(?P<line_date>\d{0,4})(?P<sign>[CD])"
                + r"(?P<amount>\d+,\d{2})N(?P<type>.{3})"
                + r".*//(?P<reference>\w{1,16}).*(?P<partner_name>.*)"
            )
        return super().get_tag_61_regex()

    def get_counterpart(self, transaction, subfield):
        """Get counterpart from transaction.

        Counterpart is often stored in subfield of tag 86. The subfield
        can be 31, 32, 33"""
        if self.env.context.get("type") == "mt940_ro_bcr":
            if not subfield:
                return  # subfield is empty
            if len(subfield) >= 1 and subfield[0]:
                transaction.update({"account_number": subfield[0]})
            if len(subfield) >= 2 and subfield[1]:
                transaction.update({"partner_name": subfield[1]})
            if len(subfield) >= 3 and subfield[2]:
                # Holds the partner VAT number
                pass
            return transaction
        return super().get_counterpart(transaction, subfield)

    def handle_tag_28(self, data, result):
        if self.env.context.get("type") == "mt940_ro_bcr":
            result["statement"]["name"] = data.replace(".", "").strip()
        else:
            super().handle_tag_28(data, result)

    def handle_tag_86(self, data, result):
        if self.env.context.get("type") == "mt940_ro_bcr":
            if result["statement"]["transactions"]:
                transaction = result["statement"]["transactions"][-1]

            if not transaction.get("name", False):
                transaction["payment_ref"] = data
                transaction["narration"] = data
                regec_ref = r"^.*Referinta (?P<ref>\w{16})"
                regec_p = r".*Platitor(?P<platitor>.*)(?P<iban_p>\w{24})"
                regec_b = r".*Beneficiar(?P<beneficiar>.*)(?P<iban_b>\w{24})"
                regec_d = r".*Detalii(?P<detalii>.*)"
                regec_cfp = r".*CODFISC (?P<codfis_p>\w+)"
                regec_cfb = r".*CODFISC (?P<codfis_b>\w+)"

                tag_86_regex_v1 = re.compile(
                    regec_ref + regec_p + regec_cfp + regec_b + regec_cfb + regec_d
                )
                tag_86_regex_v2 = re.compile(
                    regec_ref + regec_b + regec_cfb + regec_p + regec_cfp + regec_d
                )
                tag_86_regex_v3 = re.compile(regec_ref + regec_p + regec_b + regec_d)
                tag_86_regex_v4 = re.compile(regec_ref + regec_b + regec_p + regec_d)
                tag_86_regex_v5 = re.compile(regec_ref + regec_b + regec_p)
                tag_86_regex_v6 = re.compile(regec_ref + regec_b + regec_p)

                re_86 = tag_86_regex_v1.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v2.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v3.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v4.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v5.match(data)
                if not re_86:
                    re_86 = tag_86_regex_v6.match(data)

                if re_86:
                    parsed_data = re_86.groupdict()
                    if transaction["amount"] > 0:
                        transaction["partner_name"] = parsed_data.get(
                            "platitor", ""
                        ).strip()
                        transaction["account_number"] = parsed_data.get("iban_p")
                        vat = parsed_data.get("codfis_p")

                    else:
                        transaction["partner_name"] = parsed_data.get(
                            "beneficiar", ""
                        ).strip()
                        transaction["account_number"] = parsed_data.get("iban_b")
                        vat = parsed_data.get("codfis_b")
                    if vat:
                        domain = [
                            ("l10n_ro_vat_number", "=", vat),
                            ("is_company", "=", True),
                        ]
                        partner = self.env["res.partner"].search(domain, limit=1)
                        if partner:
                            transaction["partner_name"] = partner.name
                            transaction["partner_id"] = partner.id
                    if parsed_data.get("detalii"):
                        transaction["payment_ref"] = parsed_data.get("detalii")

                    transaction["ref"] = parsed_data.get("ref")
            return result
        else:
            return super().handle_tag_86(data, result)
