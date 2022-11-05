# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = 'l10n.ro.account.bank.statement.import.mt940.parser'

    def get_tag_61_regex(self):
        if self.get_mt940_type() == "mt940_ro_ing":
            return re.compile(
                r"^(?P<date>\d{6})"
                r"(?P<sign>[CD])[NR](?P<amount>\d+,\d{2})N(?P<type>.{3})"
                r"(?P<reference>\w{0,16})"
                r"(//(?P<ingid>\w{0,14})-(?P<ingtranscode>\w{0,34})){0,1}"
            )
        return super().get_tag_61_regex()

    def is_mt940(self, line):
        """determine if a line is the header of a statement"""
        if self.get_mt940_type() == "mt940_ro_ing":
            if not bool(re.match(self.get_header_regex(), line)):
                raise ValueError(
                    "File starting with %s does not seem to be a"
                    " valid %s MT940 format bank statement."
                    % (line[:4], self.get_mt940_type())
                )
        else:
            return super().is_mt940(line)

    def is_mt940_statement(self, line):
        """determine if line is the start of a statement"""
        if self.get_mt940_type() == "mt940_ro_ing":
            if not bool(line.startswith(":20:")):
                raise ValueError(
                    "The pre processed match %s does not seem to be a"
                    " valid %s MT940 format bank statement. Every statement"
                    " should start be a dict starting with :20:.." % line
                )
        else:
            return super().is_mt940_statement(line)

    def pre_process_data(self, data):
        if self.get_mt940_type() == "mt940_ro_ing":
            matches = []
            self.is_mt940(line=data)
            data = data.replace(
                '-}', '}').replace('}{', '}\r\n{').replace('\r\n', '\n')
            if data.startswith(':20:'):
                for statement in data.split(':20:'):
                    match = ':20:' + statement
                    matches.append(match)
                return matches
        return super().pre_process_data(data)

    def get_codewords(self):
        if self.get_mt940_type() == 'mt940_ro_ing':
            return ["6", "20", "21", "22", "23", "24", "25", "26", "27",
                    "28", "29", "32", "33", "37", "50", "92", ]
        return super(MT940Parser, self).get_codewords()

    def get_subfields(self, data, codewords):
        if self.get_mt940_type() == "mt940_ro_ing":
            subfields = {}
            current_codeword = None
            for word in data.split("~"):
                if not word and not current_codeword:
                    continue
                if word[:2] in codewords:
                    current_codeword = word[:2]
                    subfields[current_codeword] = [word[2:]]
                    continue
                if current_codeword in subfields:
                    subfields[current_codeword].append(word[2:])
            return subfields
        return super().get_subfields(data, codewords)

    def get_counterpart(self, transaction, subfield):
        """Get counterpart from transaction.

        Counterpart is often stored in subfield of tag 86. The subfield
        can be 31, 32, 33"""
        if self.get_mt940_type() == "mt940_ro_ing":
            if not subfield:
                return  # subfield is empty
            if len(subfield) >= 1 and subfield[0]:
                transaction.update({'account_number': subfield[0]})
            if len(subfield) >= 2 and subfield[1]:
                transaction.update({'partner_name': subfield[1]})
            if len(subfield) >= 3 and subfield[2]:
                # Holds the partner VAT number
                pass
        return super().get_counterpart(transaction, subfield)

    def handle_common_subfields(self, transaction, subfields):
        """Deal with common functionality for tag 86 subfields."""
        # Get counterpart from 31, 32 or 33 subfields:
        if self.get_mt940_type() == "mt940_ro_ing":
            counterpart_fields = []
            for counterpart_field in ['31', '32', '33']:
                if counterpart_field in subfields:
                    new_value = subfields[counterpart_field][0].replace('CUI/CNP', '')
                    counterpart_fields.append(new_value)
                else:
                    counterpart_fields.append('')
            if counterpart_fields:
                self.get_counterpart(transaction, counterpart_fields)
            if not transaction.get("name"):
                transaction["name"] = "/"
            # REMI: Remitter information (text entered by other party on trans.):
            if not transaction.get('payment_ref'):
                transaction['payment_ref'] = ''
            for counterpart_field in ['21', '23', '24', '25', '26', '27']:
                if counterpart_field in subfields:
                    transaction['payment_ref'] += (
                        '/'.join(x for x in subfields[counterpart_field] if x))
            # Get transaction reference subfield (might vary):
            if transaction.get('ref') in subfields:
                transaction['ref'] = ''.join(subfields[transaction['ref']])
        return super().handle_common_subfields(transaction, subfields)

    def handle_tag_28(self, data, result):
        """Sequence number within batch - normally only zeroes."""
        if result["statement"]:
            if result["statement"]["name"]:
                result["statement"]["name"] += data.replace(".", "").strip()
            else:
                result["statement"]["name"] = data
        return result

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
        if result["statement"]:
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
