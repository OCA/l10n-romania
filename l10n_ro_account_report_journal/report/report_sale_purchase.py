# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from copy import deepcopy
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class SaleJournalReport(models.TransientModel):
    _name = "report.l10n_ro_account_report_journal.report_sale_purchase"
    _description = "Report Sale Purchase Journal"

    @api.model
    def _get_forreport_invoices_payments(self, data, journal_type):
        account_move_obj = self.env["account.move"]
        date_from = data["form"]["date_from"]
        date_to = data["form"]["date_to"]
        company_id = self.env["res.company"].browse(data["form"]["company_id"][0])

        if journal_type == "sale":
            sale_purchase_domain = [
                ("move_type", "in", ["out_invoice", "out_refund", "out_receipt"])
            ]
        elif journal_type == "purchase":
            sale_purchase_domain = [
                ("move_type", "in", ["in_invoice", "in_refund", "in_receipt"])
            ]

        # invoices in period
        general_domain = [
            ("state", "=", "posted"),
            ("company_id", "=", company_id.id),
        ]
        invoices_in_period_domain = (
            general_domain
            + sale_purchase_domain
            + [("invoice_date", ">=", date_from), ("invoice_date", "<=", date_to)]
        )

        invoices_with_tax_cash_basis_ids = (
            []
        )  # id's to take also the invoices that are not in selected period

        # invoices that are older than the start date and not paid if they have
        # vat on payment must appear into this report
        older_unpaid_invoices = account_move_obj.search(
            sale_purchase_domain
            + [
                ("state", "=", "posted"),
                ("company_id", "=", company_id.id),
                ("invoice_date", "<", date_from),
                ("payment_state", "in", ["partial", "not_paid"]),
            ]
        )
        for upaid_invoice in older_unpaid_invoices:
            for line_id in upaid_invoice.invoice_line_ids:
                if line_id.display_type in ["line_section", "line_note"]:
                    continue
                if not line_id.tax_exigible:
                    invoices_with_tax_cash_basis_ids.append(upaid_invoice.id)
                    break

        # reconciled payments for vat_on_payment that exist in this period,
        # and we must put them into report.
        # this payments can be for some in invoices that are not in
        # line.tax_exigible=False   means  tax.tax_exigibility == 'on_payment'
        all_tax_cash_basis_journal_move_ids = account_move_obj.search(
            general_domain
            + [
                ("journal_id", "=", company_id.tax_cash_basis_journal_id.id),
                ("move_type", "in", ["entry"]),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
        )
        for cb_move_id in all_tax_cash_basis_journal_move_ids:
            partial_reconcile = cb_move_id.tax_cash_basis_rec_id
            debit_move_id = partial_reconcile.debit_move_id.move_id
            credit_move_id = partial_reconcile.credit_move_id.move_id
            debit_journal_type = debit_move_id.journal_id.type
            credit_journal_type = credit_move_id.journal_id.type
            if debit_journal_type == journal_type:
                invoices_with_tax_cash_basis_ids.append(debit_move_id.id)
            elif credit_journal_type == journal_type:
                invoices_with_tax_cash_basis_ids.append(credit_move_id.id)

        final_domain = [
            "|",
            ("id", "in", invoices_with_tax_cash_basis_ids),
            "&",
            "&",
            "&",
            "&",
        ] + invoices_in_period_domain
        invoices_for_report = self.env["account.move"].search(
            final_domain, order="invoice_date, name"
        )
        return invoices_for_report

    @api.model
    def _get_report_values(self, docids, data=None):
        company_id = data["form"]["company_id"]
        date_from = data["form"]["date_from"]
        date_to = data["form"]["date_to"]
        journal_type = data["form"]["journal_type"]
        invoices = self._get_forreport_invoices_payments(data, journal_type)

        show_warnings = data["form"]["show_warnings"]
        report_type_sale = journal_type == "sale"

        report_lines, totals = self.compute_report_lines(
            invoices, data, show_warnings, report_type_sale
        )

        docargs = {
            "print_datetime": fields.datetime.now(),
            "date_from": date_from,
            "date_to": date_to,
            "show_warnings": show_warnings,
            "user": self.env.user.name,
            "company": self.env["res.company"].browse(company_id[0]),
            "lines": report_lines,
            "totals": totals,
            "report_type_sale": report_type_sale,
        }
        return docargs

    def compute_report_lines(
        self, invoices, data, show_warnings=False, report_type_sale=True
    ):
        """input:
        invoices = account.move list of invoices to be showed in report
        payments = account.move list of payments done on vat_on_payment invoices
        vat_on_payment_reconcile = partial.reconcile  list of efective accounting
                                   moves that are telling what taxes are to be paid
        data = dictionary with selected options like date_from, date_to, company...

        returns a list of a dictionary for table with the key as column
        and total dictionary with the sums of columns """

        if not invoices:
            return [], {}
        account_partial_reconcile_obj = self.env["account.partial.reconcile"]

        sale_and_purchase_comun_columns = {
            "base_neex": {
                "type": "int",
                "tags": [
                    "-09_1 - BAZA",
                    "+09_1 - BAZA",
                    "-10_1 - BAZA",
                    "+10_1 - BAZA",
                    "-11_1 - BAZA",
                    "+11_1 - BAZA",
                ],
            },  # vat on payment
            "tva_neex": {
                "type": "int",
                "tags": [
                    "-09_1 - TVA",
                    "+09_1 - TVA",
                    "-10_1 - TVA",
                    "+10_1 - TVA",
                    "-11_1 - TVA",
                    "+11_1 - TVA",
                ],
            },
            "tva_exig": {"type": "int", "tags": []},  # what was payed  =sum of base
            "base_exig": {"type": "int", "tags": []},  # vat on payment =sum of vat
            # payment must have number,date,amount(value), base, vat
            "base_ded1": {"type": "int", "tags": []},  # intracomunitar servicii
            "base_ded2": {"type": "int", "tags": []},  # intracomunitar bunuri
            "base_19": {"type": "int", "tags": ["-09_1 - BAZA", "+09_1 - BAZA"]},
            "base_9": {"type": "int", "tags": ["-10_1 - BAZA", "+10_1 - BAZA"]},
            "base_5": {"type": "int", "tags": ["-11_1 - BAZA", "+11_1 - BAZA"]},
            "base_0": {"type": "int", "tags": ["-14 - BAZA", "+14 - BAZA"]},
            "tva_19": {"type": "int", "tags": ["-09_1 - TVA", "+09_1 - TVA"]},
            "tva_9": {"type": "int", "tags": ["-10_1 - TVA", "+10_1 - TVA"]},
            "tva_5": {"type": "int", "tags": ["-11_1 - TVA", "+11_1 - TVA"]},
            "tva_bun": {"type": "int", "tags": []},
            "tva_serv": {"type": "int", "tags": []},
            "base_col": {"type": "int", "tags": []},
            "tva_col": {"type": "int", "tags": []},
            "invers": {"type": "int", "tags": ["-13 - BAZA", "+13 - BAZA"]},
            "neimp": {"type": "int", "tags": []},
            "others": {"type": "int", "tags": []},
            "scutit1": {
                "type": "int",
                "tags": ["-14 - BAZA", "+14 - BAZA"],
            },  # cu drept de deducere
            "scutit2": {
                "type": "int",
                "tags": ["-15 - BAZA", "+15 - BAZA"],
            },  # fara drept de deducere
            "payments": {"type": "list", "tags": []},
            "warnings": {"type": "char", "tags": []},
        }
        sumed_columns = {
            "total_base": ["base_19", "base_9", "base_5", "base_0", "base_exig"],
            "total_vat": [
                "tva_19",
                "tva_9",
                "tva_5",
                "tva_bun",
                "tva_serv",
                "tva_exig",
            ],
        }  # must be int
        all_known_tags = {}
        for k, v in sale_and_purchase_comun_columns.items():
            for tag in v["tags"]:
                if tag in all_known_tags.keys():
                    all_known_tags[tag] += [k]
                    warn = (
                        f"tag='{tag}' exist in column={k} but "
                        f"also in column='{all_known_tags[tag]}'"
                    )
                    _logger.warning(warn)
                    # raise ValidationError(warn )
                else:
                    all_known_tags[tag] = [k]

        empty_row = {k: 0.0 for k in sumed_columns}
        empty_row.update(
            {
                k: 0.0
                for k, v in sale_and_purchase_comun_columns.items()
                if v["type"] == "int"
            }
        )
        empty_row.update(
            {
                k: ""
                for k, v in sale_and_purchase_comun_columns.items()
                if v["type"] == "char"
            }
        )
        empty_row.update(
            {
                k: []
                for k, v in sale_and_purchase_comun_columns.items()
                if v["type"] == "list"
            }
        )

        sign = 1 if report_type_sale else -1
        report_lines = []
        for inv1 in invoices:
            vals = deepcopy(empty_row)
            vals["number"] = inv1.name
            vals["date"] = inv1.invoice_date
            vals[
                "partner"
            ] = inv1.commercial_partner_id.name  # invoice_partner_display_name
            vals["vat"] = inv1.invoice_partner_display_vat
            vals["total"] = sign * (inv1.amount_total_signed)
            vals["warnings"] = ""
            vals["rowspan"] = 1

            put_payments = False
            # after parsing the invoice lines, if is vat on payment,
            # to put also the payments take all the lines from this
            # invoice and put them into dictionary
            for line in inv1.line_ids:
                if line.display_type in ["line_section", "line_note"]:
                    continue
                if line.account_id.code.startswith(
                    "411"
                ) or line.account_id.code.startswith("401"):
                    if vals["total"] != sign * (-line.credit + line.debit):
                        vals["warnings"] += (
                            f"The value of invoice is {vals['total']} but "
                            f"accounting account {line.account_id.code} has "
                            f"a value of  {sign*(-line.credit+line.debit)}"
                        )
                else:
                    unknown_line = True
                    if not line.tax_exigible:  # VAT on payment
                        put_payments = True
                        for tag in line.tax_tag_ids:
                            # adding the base and vat from original invoice
                            if (
                                tag.name
                                in sale_and_purchase_comun_columns["base_neex"]["tags"]
                            ):
                                vals["base_neex"] += sign * (line.credit - line.debit)
                                unknown_line = False
                            elif (
                                tag.name
                                in sale_and_purchase_comun_columns["tva_neex"]["tags"]
                            ):
                                vals["tva_neex"] += sign * (line.credit - line.debit)
                                unknown_line = False

                    else:  # NOT VAT on payment
                        if not line.tax_tag_ids:
                            vals["base_0"] += sign * (line.credit - line.debit)
                            unknown_line = False
                        else:
                            for tag in line.tax_tag_ids:
                                if tag.name in all_known_tags.keys():
                                    for tagx in all_known_tags[tag.name]:
                                        if tagx not in [
                                            "tva_neex",
                                            "base_neex",
                                        ]:
                                            vals[tagx] += sign * (
                                                line.credit - line.debit
                                            )
                                    unknown_line = False
                        if unknown_line:
                            vals["warnings"] += (
                                f"unknown report column for line {line.name} debit={line.debit} "
                                f"credit={line.credit} TAGS{[x.name for x in line.tax_tag_ids]};"
                            )

            if put_payments:
                # This invoice is vat on payment and we are going to put the payments
                # search the reconcile line
                reconcile_account_move_line_id = False
                for line in inv1.line_ids:
                    if line.account_id.code.startswith(
                        "411"
                    ) or line.account_id.code.startswith("401"):
                        reconcile_account_move_line_id = line.id
                        break
                # find all the reconciliation till date to
                all_reconcile = account_partial_reconcile_obj.search(
                    [
                        "|",
                        ("debit_move_id", "=", reconcile_account_move_line_id),
                        ("credit_move_id", "=", reconcile_account_move_line_id),
                        ("company_id", "=", data["form"]["company_id"][0]),
                        ("max_date", "<=", data["form"]["date_to"]),
                    ]
                )
                all_reconcile_ids = [x.id for x in all_reconcile]

                for move in self.env["account.move"].search(
                    [("tax_cash_basis_rec_id", "in", all_reconcile_ids)]
                ):
                    if (
                        move.date
                        < datetime.strptime(
                            data["form"]["date_from"], DEFAULT_SERVER_DATE_FORMAT
                        ).date()
                    ):
                        # this payment is in a period before and we will just substract it
                        for move_line in move.line_ids:
                            for tag in move_line.tax_tag_ids:
                                if (
                                    tag.name
                                    in sale_and_purchase_comun_columns["base_neex"][
                                        "tags"
                                    ]
                                ):
                                    vals["base_neex"] -= sign * (
                                        move_line.credit - move_line.debit
                                    )
                                elif (
                                    tag.name
                                    in sale_and_purchase_comun_columns["tva_neex"][
                                        "tags"
                                    ]
                                ):
                                    vals["tva_neex"] -= sign * (
                                        move_line.credit - move_line.debit
                                    )
                    else:
                        # is payment in period and we are going also to show it, and also substract it
                        vals["rowspan"] += 1
                        vals["payments"] += [
                            {
                                "number": move.ref,
                                "date": move.date,
                                "amount": move.amount_total,
                                "base_exig": 0,
                                "tva_exig": 0,
                            }
                        ]
                        for move_line in move.line_ids:
                            if "TVA" in "".join(
                                [x.name for x in move_line.tax_tag_ids]
                            ):
                                vals["payments"][-1]["tva_exig"] += sign * (
                                    move_line.credit - move_line.debit
                                )
                            elif "BAZA" in "".join(
                                [x.name for x in move_line.tax_tag_ids]
                            ):
                                vals["payments"][-1]["base_exig"] += sign * (
                                    move_line.credit - move_line.debit
                                )
                            for tag in move_line.tax_tag_ids:
                                if tag.name in all_known_tags.keys():
                                    for tagx in all_known_tags[tag.name]:
                                        if tagx in ["base_neex", "tva_neex"]:
                                            vals[tagx] -= sign * (
                                                move_line.credit - move_line.debit
                                            )  # we substract neexigible because is exigible
                                        else:
                                            vals[tagx] += sign * (
                                                move_line.credit - move_line.debit
                                            )
            if vals["rowspan"] > 1:
                vals["rowspan"] -= 1

            vals["base_neex"], vals["tva_neex"] = (
                round(vals["base_neex"], 2),
                round(vals["tva_neex"], 2),
            )

            for key, value in sumed_columns.items():
                # put the aggregated values ( summed columns)
                vals[key] = sum([vals[x] for x in value])

            report_lines += [vals]  # we added another line to the table

        # # print extracted               for testing
        #             text=text_antet=''
        #             for key,value in vals.items():
        #                 if key in ['date','partner','total']:
        #                     text_antet += key+':'+str(value)+','
        #                 elif (type(value) is float) and value!=0:
        #                     text += f"{key}:{value};"
        #                 else:
        #                     continue
        #             print(text_antet+text)

        # make the totals dictionary for total line of table as sum of all the integer/float values of vals
        int_float_keys = []
        for key, value in report_lines[0].items():
            if (type(value) is int) or (type(value) is float):
                int_float_keys.append(key)
        totals = {}
        for key in int_float_keys:
            totals[key] = round(sum([x[key] for x in report_lines]), 2)
        totals["payments"] = []

        return report_lines, totals
