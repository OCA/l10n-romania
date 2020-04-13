# Copyright (C) 2020 OdooERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleJournalReport(models.TransientModel):
    _name = "report.l10n_ro_account_report_journal.report_sale_purchase"
    _description = "Report Sale Purchase Journal"

    @api.model
    def _get_journal_invoice_domain(self, data, journal_type):
        date_from = data["form"]["date_from"]
        date_to = data["form"]["date_to"]
        company_id = data["form"]["company_id"]
        domain = [
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
            ("company_id", "=", company_id[0]),
        ]
        if journal_type == "sale":
            domain += [("type", "in", ["out_invoice", "out_refund", "out_receipt"])]
        elif journal_type == "purchase":
            domain += [("type", "in", ["in_invoice", "in_refund", "in_receipt"])]
        return domain

    @api.model
    def _get_report_values(self, docids, data=None):
        company_id = data["form"]["company_id"]
        date_from = data["form"]["date_from"]
        date_to = data["form"]["date_to"]
        journal_type = data["form"]["journal"]
        domain = self._get_journal_invoice_domain(data, journal_type)
        invoices = self.env["account.move"].search(domain, order="invoice_date, name")

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
        self, invoices, data, show_warnings, report_type_sale=True
    ):
        """returns a list of a dictionary for table with the key as column
        and total dictionary with the sums of columns """
        # self.ensure_one()
        # find all the keys for dictionary
        # maybe posible_tags must be put manually,
        # but if so, to be the same as account.account.tag name
        if not invoices:
            return [],{}
        posible_tags = self.env["account.account.tag"].search_read(
            [
                ("country_id", "=", self.env.ref("base.ro").id),
                ("applicability", "=", "taxes"),
            ],
            ["name"],
        )
        posible_tags += [{'name': 'no_tag_like_vat0'},
                         {'name':'avans_clienti'}, 
                         ]
        
        posible_tags_just_names = [x["name"] for x in posible_tags]
#         for x in posible_tags_just_names:
#             print(f"'{x}'")

        # future posbile_tags_in_sale & posbile_tags_in_purchase and
        # if something not right

        # in aggregated_dict the key represent the new key that has as value list
        # of keys that must be summed ( children)
        aggregated_dict = {"total_base": [], "total_vat": []}
        aggregated_dict["total_base"] = [
            x
            for x in posible_tags_just_names
            if ("% (deductibila)" in x)
            or ("+Baza TVA" in x and "%" == x[-1])
            or ("-Baza TVA" in x and "%" == x[-1])
        ]
        aggregated_dict["total_vat"] = [
            x
            for x in posible_tags
            if ("% (TVA colectata)" in x) or ("% (deductibila)" in x and "TVA" in x)
        ]

        aggregated_dict['total_base'] = [x for x in posible_tags_just_names if (
                            ('+Baza TVA' in x and ('%' == x[-1] or x[-15:] == '% (deductibila)')) or
                            ('-Baza TVA' in x and ('%' == x[-1] or x[-15:] == '% (deductibila)'))  )]
        aggregated_dict['total_vat'] = [x for x in posible_tags_just_names if (
                            ("+TVA" == x[:4] and ('% (TVA colectata)' == x[-17:] or x[-15:]=='% (deductibila)')) or
                            ("-TVA" == x[:4] and ('% (TVA colectata)' == x[-17:] or x[-15:]=='% (deductibila)'))     )]

        sign = 1 if report_type_sale else -1
        report_lines = []
        for inv1 in invoices:
            vals = {x: 0 for x in posible_tags_just_names}
            vals["number"] = inv1.name
            vals["date"] = inv1.invoice_date
            vals["partner"] = inv1.invoice_partner_display_name
            vals["vat"] = inv1.invoice_partner_display_vat
            vals["total"] = sign*(inv1.amount_total_signed)
            vals["warnings"] = ""

            for line in inv1.line_ids:
                if line.account_id.code.startswith(
                    "411"
                ) or line.account_id.code.startswith("401"):
                    if vals["total"] != sign*(-line.credit + line.debit):
                        vals["warnings"] += (
                            f"The value of invoice is {vals['total']} but "
                            f"accounting account {line.account_id.code} has "
                            f"a value of  {line.credit-line.debit}"
                        )
                else:
                    if not line.tag_ids:
                        vals['no_tag_like_vat0'] += sign*(line.credit - line.debit)
                    elif len(line.tag_ids) > 1: 
                        vals["warnings"] += (
                            f"line id={line.id} name={line.name}  does not "
                            f"have line_tag_ids or have more and I'm not "
                            f"going to guess it ( maybe in future); "
                        )
                    elif line.tag_ids[0].name not in posible_tags_just_names:
                        vals["warnings"] += (
                            f"this tag_ids={line.tag_ids[0].name} is not in "
                            f"find_all_account_tax_report_line"
                        )
                    else:
                        vals[line.tag_ids[0].name] += sign*(line.credit - line.debit)
                    if line.account_id.code.startswith("419"):
                        vals['avans_clienti'] = (line.credit - line.debit) #!!!!!!!!!!!!!!! we put it only here or also at sum of bases 
            # put the aggregated values
            for key, value in aggregated_dict.items():
                vals[key] = sum([vals[x] for x in value])

            report_lines += [vals]

        # make the totals dictionary for total line of table as sum of all the
        # integer/int values of vals
        int_float_keys = []
        for key, value in report_lines[0].items():
            if (type(value) is int) or (type(value) is float):
                int_float_keys.append(key)
        totals = {}
        for key in int_float_keys:
            totals[key] = sum([x[key] for x in report_lines])
        return report_lines, totals

"""
not put into xml
    used in xml
    '-Baza TVA 0%'
    '+Baza TVA 0%'
    '-Baza TVA 19%'
    '+Baza TVA 19%'
    '-Baza TVA 24%'
    '+Baza TVA 24%'
    '-Baza TVA 5%'
    '+Baza TVA 5%'
    '-Baza TVA 9%'
    '+Baza TVA 9%'
'-Baza TVA Intracomunitar Bunuri'
'+Baza TVA Intracomunitar Bunuri'
'-Baza TVA Intracomunitar Servicii'
'+Baza TVA Intracomunitar Servicii'
    '-Baza TVA Taxare Inversa'
    '+Baza TVA Taxare Inversa'
    '-TVA 0% (TVA colectata)'
    '+TVA 0% (TVA colectata)'
    '-TVA 19% (TVA colectata)'
    '+TVA 19% (TVA colectata)'
    '-TVA 24% (TVA colectata)'
    '+TVA 24% (TVA colectata)'
    '-TVA 5% (TVA colectata)'
    '+TVA 5% (TVA colectata)'
    '-TVA 9% (TVA colectata)'
    '+TVA 9% (TVA colectata)'
'-TVA Intracomunitar Bunuri (TVA colectata)'
'+TVA Intracomunitar Bunuri (TVA colectata)'
'-TVA Intracomunitar Servicii (TVA colectata)'
'+TVA Intracomunitar Servicii (TVA colectata)'
'-TVA Taxare Inversa (TVA colectata)'
'+TVA Taxare Inversa (TVA colectata)'
    '-Baza TVA 0% (deductibila)'
    '+Baza TVA 0% (deductibila)'
    '-Baza TVA 19% (deductibila)'
    '+Baza TVA 19% (deductibila)'
    '-Baza TVA 24% (deductibila)'
    '+Baza TVA 24% (deductibila)'
    '-Baza TVA 5% (deductibila)'
    '+Baza TVA 5% (deductibila)'
    '-Baza TVA 9% (deductibila)'
    '+Baza TVA 9% (deductibila)'
    '-Baza TVA Intracomunitar Bunuri (deductibila)'
    '+Baza TVA Intracomunitar Bunuri (deductibila)'
    '-Baza TVA Intracomunitar Servicii (deductibila)'
    '+Baza TVA Intracomunitar Servicii (deductibila)'
    '-Baza TVA Taxare Inversa (deductibila)'
    '+Baza TVA Taxare Inversa (deductibila)'
'-TVA 0%'
'+TVA 0%'
    '-TVA 19% (deductibila)'
    '+TVA 19% (deductibila)'
    '-TVA 24% (deductibila)'
    '+TVA 24% (deductibila)'
    '-TVA 5% (deductibila)'
    '+TVA 5% (deductibila)'
    '-TVA 9% (deductibila)'
    '+TVA 9% (deductibila)'
    '-TVA Intracomunitar Bunuri (deductibila)'
    '+TVA Intracomunitar Bunuri (deductibila)'
    '-TVA Intracomunitar Servicii (deductibila)'
    '+TVA Intracomunitar Servicii (deductibila)'
    '-TVA Taxare Inversa (deductibila)'
    '+TVA Taxare Inversa (deductibila)'
    '-Baza TVA Taxare Scutita - Achizitii'
    '+Baza TVA Taxare Scutita - Achizitii'
'-Baza TVA Taxare Scutita - Vanzari'
'+Baza TVA Taxare Scutita - Vanzari'
    '-Baza TVA Taxare intracomunitara neimpozabila - Achizitii'
    '+Baza TVA Taxare intracomunitara neimpozabila - Achizitii'
'-Baza TVA Taxare intracomunitara neimpozabila - Vanzari'
'+Baza TVA Taxare intracomunitara neimpozabila - Vanzari'
"""
