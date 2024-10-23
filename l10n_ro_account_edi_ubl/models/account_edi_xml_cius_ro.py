# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountEdiXmlCIUSRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

    def _get_tax_category_list(self, invoice, taxes):
        vals_list = super()._get_tax_category_list(invoice, taxes)
        for vals in vals_list:
            word_to_check = "Invers"
            if any(
                word_to_check.lower() in word.lower() for word in taxes.mapped("name")
            ):
                vals["id"] = "AE"
                vals["tax_category_code"] = "AE"
                vals["tax_exemption_reason_code"] = "VATEX-EU-AE"
                vals["tax_exemption_reason"] = ""
            if vals["percent"] == 0 and vals["tax_category_code"] != "AE":
                vals["id"] = "Z"
                vals["tax_category_code"] = "Z"
                vals["tax_exemption_reason"] = ""

        return vals_list

    # def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
    #     vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
    #     if (
    #         invoice.move_type in ["out_refund", "in_refund"]
    #     ):
    #         vals_list[0].update(
    #             {"tax_amount": -1 * taxes_vals["tax_amount_currency"]}
    #         )
    #         for vals in taxes_vals["tax_details"].values():
    #             vals["taxable_amount"] = -1 * vals["base_amount_currency"]
    #             vals["tax_amount"] = -1 * vals["tax_amount_currency"]
    #     return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        balance_sign = 1
        if invoice.move_type in ["out_refund", "in_refund"]:
            balance_sign = -balance_sign

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
                        "tax_id": vals["group_tax_details"][0]["id"],
                    }
                    for vals in taxes_vals["tax_details"].values()
                ],
            }
        ]

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        res = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        if line.move_id.move_type in ["out_refund", "in_refund"]:
            if res.get("line_quantity", 0):
                res["line_quantity"] = (-1) * res["line_quantity"]
            if res.get("line_extension_amount", 0):
                res["line_extension_amount"] = (-1) * res["line_extension_amount"]
            if res.get("tax_total_vals"):
                for tax in res["tax_total_vals"]:
                    if tax["tax_amount"]:
                        tax["tax_amount"] = (-1) * tax["tax_amount"]
                    if tax["taxable_amount"]:
                        tax["taxable_amount"] = (-1) * tax["taxable_amount"]
        return res

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        vals["description"] = vals["description"][:200]
        vals["name"] = vals["name"][:100]
        if vals["classified_tax_category_vals"]:
            if vals["classified_tax_category_vals"][0]["tax_category_code"] == "AE":
                vals["classified_tax_category_vals"][0][
                    "tax_exemption_reason_code"
                ] = ""
                vals["classified_tax_category_vals"][0]["tax_exemption_reason"] = ""
        return vals

    def _get_invoice_line_price_vals(self, line):
        vals = super()._get_invoice_line_price_vals(line)
        vals["base_quantity"] = 1.0
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        if not partner.vat and partner.company_registry:
            vals_list = [
                {
                    "company_id": partner.company_registry,
                    "tax_scheme_vals": {"id": "VAT"},
                }
            ]
        for vals in vals_list:
            if partner.country_code == "RO" and not (
                vals["company_id"] or ""
            ).upper().startswith("RO"):
                vals["tax_scheme_vals"]["id"] = "!= VAT"

        return vals_list

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        if vals.get("vals"):
            invoice_vals = vals["vals"]
            if invoice_vals.get("order_reference"):
                invoice_vals["order_reference"] = invoice_vals["order_reference"][:30]
            if invoice_vals.get("sales_order_id"):
                invoice_vals["sales_order_id"] = invoice_vals["sales_order_id"][:200]
            if invoice.move_type in ["out_refund", "in_refund"]:
                if invoice_vals.get("monetary_total_vals"):
                    invoice_vals["monetary_total_vals"]["tax_exclusive_amount"] = (
                        -1
                    ) * invoice_vals["monetary_total_vals"]["tax_exclusive_amount"]
                    invoice_vals["monetary_total_vals"]["tax_inclusive_amount"] = (
                        -1
                    ) * invoice_vals["monetary_total_vals"]["tax_inclusive_amount"]
                    invoice_vals["monetary_total_vals"]["prepaid_amount"] = (
                        -1
                    ) * invoice_vals["monetary_total_vals"]["prepaid_amount"]
                    invoice_vals["monetary_total_vals"]["payable_amount"] = (
                        -1
                    ) * invoice_vals["monetary_total_vals"]["payable_amount"]
            if invoice.is_l10n_ro_autoinvoice():
                customer = invoice.company_id.partner_id.commercial_partner_id
                supplier = invoice.partner_id
                vals.update({"customer": customer, "supplier": supplier})
                customer_vals = invoice_vals["accounting_customer_party_vals"]
                invoice_vals.update(
                    {
                        "accounting_customer_party_vals": invoice_vals[
                            "accounting_supplier_party_vals"
                        ],
                        "accounting_supplier_party_vals": customer_vals,
                    }
                )
            vals["main_template"] = "account_edi_ubl_cii.ubl_20_Invoice"
            invoice_vals["invoice_type_code"] = 380
            invoice_vals["document_type_code"] = 380
            if invoice_vals.get("credit_note_type_code"):
                invoice_vals.pop("credit_note_type_code")
            if (
                invoice.move_type in ("in_invoice", "in_refund")
                and invoice.journal_id.l10n_ro_sequence_type == "autoinv2"
            ) or (
                invoice.journal_id.type == "sale"
                and invoice.journal_id.l10n_ro_sequence_type == "autoinv1"
            ):
                invoice_vals["document_type_code"] = 389
                invoice_vals["invoice_type_code"] = 389
            point_of_sale = (
                self.env["ir.module.module"]
                .sudo()
                .search(
                    [("name", "=", "point_of_sale"), ("state", "=", "installed")],
                    limit=1,
                )
            )
            if point_of_sale:
                if invoice.pos_order_ids:
                    invoice_vals["document_type_code"] = 751
                    invoice_vals["invoice_type_code"] = 751
        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        res = super()._get_invoice_payment_means_vals_list(invoice)
        if not invoice.partner_bank_id:
            for vals in res:
                vals.update(
                    {
                        "payment_means_code": "1",
                        "payment_means_code_attrs": {"name": "Not Defined"},
                    }
                )
        return res

    def _import_fill_invoice_line_form(self, tree, invoice_line, qty_factor):
        res = super()._import_fill_invoice_line_form(tree, invoice_line, qty_factor)

        tax_nodes = tree.findall(".//{*}Item/{*}ClassifiedTaxCategory/{*}ID")
        if len(tax_nodes) == 1:
            if tax_nodes[0].text in ["O", "E", "Z"]:
                # Acest TVA nu generaza inregistrari contabile,
                # deci putem lua orice primul tva pe cota 0
                # filtrat dupa companie si tip jurnal.
                journal = invoice_line.move_id.journal_id
                tax = self.env["account.tax"].search(
                    [
                        ("amount", "=", "0"),
                        ("type_tax_use", "=", journal.type),
                        ("amount_type", "=", "percent"),
                        ("company_id", "=", invoice_line.company_id.id),
                    ],
                    limit=1,
                )
                if tax and not invoice_line.tax_ids:
                    invoice_line.tax_ids.add(tax)
        return res

    def _import_fill_invoice_line_taxes(
        self, tax_nodes, invoice_line, inv_line_vals, logs
    ):
        if not invoice_line.account_id:
            invoice_line.account_id = invoice_line.move_id.journal_id.default_account_id
        if not inv_line_vals.get("account_id"):
            inv_line_vals[
                "account_id"
            ] = invoice_line.move_id.journal_id.default_account_id.id
        return super()._import_fill_invoice_line_taxes(
            tax_nodes, invoice_line, inv_line_vals, logs
        )

    def _get_document_type_code_vals(self, invoice, invoice_data):
        # EXTENDS 'account_edi_ubl_cii
        vals = super()._get_document_type_code_vals(invoice, invoice_data)
        # [UBL-SR-43] DocumentTypeCode should only show up on a CreditNote
        # XML with the value '50'
        if invoice.move_type == "in_refund" and invoice.is_l10n_ro_autoinvoice():
            vals["value"] = "50"
        return vals

    def _import_retrieve_and_fill_partner(
        self,
        invoice,
        name,
        phone,
        mail,
        vat,
        country_code=False,
        peppol_eas=False,
        peppol_endpoint=False,
    ):
        """Update method to set the partner as a company, not individual"""
        res = super()._import_retrieve_and_fill_partner(
            invoice, name, phone, mail, vat, country_code, peppol_eas, peppol_endpoint
        )
        if country_code == "RO":
            if not invoice.partner_id.is_company and name and vat:
                invoice.partner_id.is_company = True
                invoice.partner_id.ro_vat_change()
        return res

    def _import_retrieve_partner_vals(self, tree, role):
        vals = super()._import_retrieve_partner_vals(tree, role)
        name = self._find_value(
            f"//cac:Accounting{role}Party/cac:Party//cac:PartyLegalEntity//cbc:RegistrationName",  # noqa: B950
            tree,
        )
        if name:
            vals["name"] = name
        return vals
