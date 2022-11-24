# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountEdiXmlCIUSRO(models.Model):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.cius_ro"
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_address_vals(partner)
        # CIUS-RO country_subentity formed as country_code + state code
        if partner and partner.state_id:
            vals["country_subentity"] = (
                partner.state_id.country_id.code + "-" + partner.state_id.code
            )
        # CIUS-RO replace spaces in city -- for Sector 1 -> Sector1
        if partner.state_id.code == "B" and "sector" in partner.city:
            vals["city"] = partner.city.upper().replace(" ", "")
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        for vals in vals_list:
            # /!\ For Romanian companies, the company_id can be with or without country code.
            if (
                partner.country_id.code == "RO"
                and partner.vat
                and not partner.vat.upper().startswith("RO")
            ):
                vals["tax_scheme_id"] = "!= VAT"
        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        balance_sign = -1 if invoice.is_inbound() else 1
        return [
            {
                "currency": invoice.currency_id,
                "currency_dp": invoice.currency_id.decimal_places,
                "tax_amount": balance_sign * taxes_vals["tax_amount_currency"],
                "tax_subtotal_vals": [
                    {
                        "currency": invoice.currency_id,
                        "currency_dp": invoice.currency_id.decimal_places,
                        "taxable_amount": balance_sign * vals["base_amount_currency"],
                        "tax_amount": balance_sign * vals["tax_amount_currency"],
                        "percent": vals["_tax_category_vals_"]["percent"],
                        "tax_category_vals": vals["_tax_category_vals_"],
                        "tax_id": vals["group_tax_details"][0]["tax_id"],
                    }
                    for vals in taxes_vals["tax_details"].values()
                ],
            }
        ]

    def _get_invoice_line_price_vals(self, line):
        vals = super()._get_invoice_line_price_vals(line)
        vals["base_quantity"] = line.quantity
        return vals

    def _export_invoice_vals(self, invoice):
        vals_list = super()._export_invoice_vals(invoice)
        vals_list["vals"]["order_reference"] = (invoice.ref or invoice.name)[:30]
        vals_list[
            "TaxTotalType_template"
        ] = "l10n_ro_account_edi_ubl.ubl_20_TaxTotalType"
        vals_list["vals"][
            "customization_id"
        ] = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0"
        index = 1
        for val in vals_list["vals"]["invoice_line_vals"]:
            val["id"] = index
            index += 1
        # amount = 0
        # tax_subtotal_vals = vals_list["vals"]["tax_total_vals"][0]["tax_subtotal_vals"]
        # for tax in tax_subtotal_vals:
        #     invoice_totals = json.loads(invoice.tax_totals_json)
        #     for tax_group in invoice_totals['groups_by_subtotal'].values():
        #         if tax_group[0] == tax["tax_id"].tax_group_id.name:
        #             tax["tax_amount"] = tax_group[1]
        #             amount += tax_group[1]
        # vals_list["vals"]["tax_total_vals"][0]["tax_amount"] = amount

        if invoice.move_type == "out_refund":
            vals_list["main_template"] = "account_edi_ubl_cii.ubl_20_Invoice"
            vals_list["vals"]["invoice_type_code"] = 380
            vals_list["vals"].pop("credit_note_type_code")
            for line in vals_list["vals"]["invoice_line_vals"]:
                line["invoiced_quantity"] = -1 * line["invoiced_quantity"]
                line["line_extension_amount"] = -1 * line["line_extension_amount"]
            total_vals = vals_list["vals"]["legal_monetary_total_vals"]
            total_vals["line_extension_amount"] = (
                -1 * total_vals["line_extension_amount"]
            )
            total_vals["tax_exclusive_amount"] = -1 * total_vals["tax_exclusive_amount"]
            total_vals["tax_inclusive_amount"] = -1 * total_vals["tax_inclusive_amount"]
            total_vals["payable_amount"] = -1 * total_vals["payable_amount"]
            for tax in vals_list["vals"]["tax_total_vals"]:
                tax["tax_amount"] = -1 * tax["tax_amount"]
                for subtax in tax["tax_subtotal_vals"]:
                    subtax["taxable_amount"] = -1 * subtax["taxable_amount"]
                    subtax["tax_amount"] = -1 * subtax["tax_amount"]

        return vals_list
