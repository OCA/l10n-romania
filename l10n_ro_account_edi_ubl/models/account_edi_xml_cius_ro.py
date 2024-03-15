# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from base64 import b64decode, b64encode

import requests

from odoo import _, api, models

SECTOR_RO_CODES = ("SECTOR1", "SECTOR2", "SECTOR3", "SECTOR4", "SECTOR5", "SECTOR6")


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
        if partner.state_id.code == "B" and "sector" in (partner.city or "").lower():
            vals["city_name"] = partner.city.upper().replace(" ", "")
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

    def _get_tax_category_list(self, invoice, taxes):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_tax_category_list(invoice, taxes)
        # for vals in vals_list:
        #     vals.pop('tax_exemption_reason', None)
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

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        balance_sign = -1 if invoice.is_inbound() else 1
        if (
            invoice.move_type in ["out_refund", "in_refund"]
            and invoice.company_id.l10n_ro_credit_note_einvoice
        ):
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
                        "tax_id": vals["group_tax_details"][0]["tax_id"],
                    }
                    for vals in taxes_vals["tax_details"].values()
                ],
            }
        ]

    def _get_delivery_vals_list(self, invoice):
        res = super()._get_delivery_vals_list(invoice)

        shipping_address = False
        if "partner_shipping_id" in invoice._fields and invoice.partner_shipping_id:
            shipping_address = invoice.partner_shipping_id
            if shipping_address == invoice.partner_id:
                shipping_address = False
        if shipping_address:
            res = [
                {
                    "actual_delivery_date": invoice.invoice_date,
                    "delivery_location_vals": {
                        "delivery_address_vals": self._get_partner_address_vals(
                            shipping_address
                        ),
                    },
                }
            ]
        return res

    def _get_invoice_line_vals(self, line, taxes_vals):
        res = super()._get_invoice_line_vals(line, taxes_vals)
        if line.discount != 0:
            discount_amount = line.price_unit * line.quantity * line.discount / 100
            if res.get("line_extension_amount", 0):
                res["line_extension_amount"] = (
                    discount_amount + res["line_extension_amount"]
                )
        if (
            line.move_id.move_type in ["out_refund", "in_refund"]
            and line.company_id.l10n_ro_credit_note_einvoice
        ):
            if res.get("invoiced_quantity", 0):
                res["invoiced_quantity"] = (-1) * res["invoiced_quantity"]
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

    def split_string(self, string):
        return [string[i : i + 100] for i in range(0, len(string), 100)]

    def _export_invoice_vals(self, invoice):
        vals_list = super()._export_invoice_vals(invoice)
        vals_list["vals"]["buyer_reference"] = (
            invoice.commercial_partner_id.ref or invoice.commercial_partner_id.name
        )
        vals_list["vals"]["order_reference"] = (invoice.ref or invoice.name)[:30]
        vals_list[
            "TaxTotalType_template"
        ] = "l10n_ro_account_edi_ubl.ubl_20_TaxTotalType"
        vals_list["vals"][
            "customization_id"
        ] = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
        index = 1
        for val in vals_list["vals"]["invoice_line_vals"]:
            val["id"] = index
            index += 1

        if (
            invoice.move_type in ["out_refund", "in_refund"]
            and invoice.company_id.l10n_ro_credit_note_einvoice
        ):
            if vals_list["vals"].get("legal_monetary_total_vals"):
                vals_list["vals"]["legal_monetary_total_vals"][
                    "tax_exclusive_amount"
                ] = (-1) * vals_list["vals"]["legal_monetary_total_vals"][
                    "tax_exclusive_amount"
                ]
                vals_list["vals"]["legal_monetary_total_vals"][
                    "tax_inclusive_amount"
                ] = (-1) * vals_list["vals"]["legal_monetary_total_vals"][
                    "tax_inclusive_amount"
                ]
                vals_list["vals"]["legal_monetary_total_vals"]["prepaid_amount"] = (
                    -1
                ) * vals_list["vals"]["legal_monetary_total_vals"]["prepaid_amount"]
                vals_list["vals"]["legal_monetary_total_vals"]["payable_amount"] = (
                    -1
                ) * vals_list["vals"]["legal_monetary_total_vals"]["payable_amount"]
        if (
            invoice.journal_id.l10n_ro_sequence_type == "autoinv2"
            and invoice.journal_id.l10n_ro_partner_id
        ):
            customer = vals_list.get(
                "customer", invoice.company_id.partner_id.commercial_partner_id
            )
            vals_list["customer"] = vals_list["supplier"]
            vals_list["supplier"] = customer
            customer_vals = vals_list["vals"]["accounting_customer_party_vals"]
            vals_list["vals"]["accounting_customer_party_vals"] = vals_list["vals"][
                "accounting_supplier_party_vals"
            ]
            vals_list["vals"]["accounting_supplier_party_vals"] = customer_vals
        if invoice.move_type in ("out_invoice", "in_invoice"):
            vals_list["main_template"] = "account_edi_ubl_cii.ubl_20_Invoice"
            vals_list["vals"]["invoice_type_code"] = 380
        else:
            vals_list["main_template"] = "account_edi_ubl_cii.ubl_20_CreditNote"
            vals_list["vals"]["credit_note_type_code"] = 381
        result_list = []
        if vals_list["vals"].get("note_vals"):
            if len(vals_list["vals"]["note_vals"][0]) > 100:
                split_strings = self.split_string(vals_list["vals"]["note_vals"][0])
                for _index, split_str in enumerate(split_strings):
                    result_list.append(split_str)
        if result_list:
            vals_list["vals"]["note_vals"] = result_list
        return vals_list

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii' preluate din Odoo 17.0
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ("supplier", "customer"):
            partner = vals[partner_type]

            if partner.is_company:
                constraints.update(
                    {
                        f"ciusro_{partner_type}_city_required": self._check_required_fields(
                            partner, "city"
                        ),
                        f"ciusro_{partner_type}_street_required": self._check_required_fields(
                            partner, "street"
                        ),
                        f"ciusro_{partner_type}_state_id_required": self._check_required_fields(
                            partner, "state_id"
                        ),
                    }
                )
                if not partner.vat:
                    constraints[f"ciusro_{partner_type}_tax_identifier_required"] = _(
                        "The following partner doesn't have a VAT nor Company ID: %s. "
                        "At least one of them is required. ",
                        partner.name,
                    )

                if (
                    partner.l10n_ro_vat_subjected
                    and partner.vat
                    and not partner.vat.startswith(partner.country_id.code)
                ):
                    constraints[f"ciusro_{partner_type}_country_code_vat_required"] = _(
                        "The following partner's doesn't have a "
                        "country code prefix in their VAT: %s.",
                        partner.name,
                    )
                if (
                    partner.country_id.code == "RO"
                    and partner.state_id
                    and partner.state_id.code == "B"
                ):
                    # Use send city to check if it's a valid sector
                    # because when they come from ANAF, not all are
                    # formatted as SECTORX
                    send_city = partner.city.upper().replace(" ", "")
                    if send_city not in SECTOR_RO_CODES:
                        constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                            "The following partner's city name is invalid: %s. "
                            "If partner's state is București, the city name must be 'SECTORX', "
                            "where X is a number between 1-6.",
                            partner.name,
                        )

        return constraints

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

    def _import_fill_invoice_line_form(
        self, journal, tree, invoice, invoice_line, qty_factor
    ):
        res = super(AccountEdiXmlCIUSRO, self)._import_fill_invoice_line_form(
            journal, tree, invoice, invoice_line, qty_factor
        )
        tax_nodes = tree.findall(".//{*}Item/{*}ClassifiedTaxCategory/{*}ID")
        if len(tax_nodes) == 1:
            if tax_nodes[0].text in ["O", "E", "Z"]:
                # Acest TVA nu generaza inregistrari contabile,
                # deci putem lua orice primul tva pe cota 0
                # filtrat dupa companie si tip jurnal.
                tax = self.env["account.tax"].search(
                    [
                        ("amount", "=", "0"),
                        ("type_tax_use", "=", journal.type),
                        ("amount_type", "=", "percent"),
                        ("company_id", "=", invoice.company_id.id),
                    ],
                    limit=1,
                )
                if tax:
                    invoice_line.tax_ids.add(tax)
        return res

    def _import_fill_invoice_line_taxes(
        self, journal, tax_nodes, invoice_line_form, inv_line_vals, logs
    ):
        if not invoice_line_form.account_id:
            invoice_line_form.account_id = journal.default_account_id
        if not inv_line_vals.get("account_id"):
            inv_line_vals["account_id"] = journal.default_account_id.id
        return super()._import_fill_invoice_line_taxes(
            journal, tax_nodes, invoice_line_form, inv_line_vals, logs
        )

    @api.model
    def _retrieve_partner_with_vat(self, vat, extra_domain):
        company_domain = [("is_company", "=", True)]
        extra_domain = extra_domain + company_domain if extra_domain else company_domain
        return super()._retrieve_partner_with_vat(vat, extra_domain)

    @api.model
    def _retrieve_partner_with_phone_mail(self, phone, mail, extra_domain):
        company_domain = [("is_company", "=", True)]
        extra_domain = extra_domain + company_domain if extra_domain else company_domain
        return super()._retrieve_partner_with_phone_mail(phone, mail, extra_domain)

    @api.model
    def _retrieve_partner_with_name(self, name, extra_domain):
        company_domain = [("is_company", "=", True)]
        extra_domain = extra_domain + company_domain if extra_domain else company_domain
        return super()._retrieve_partner_with_name(name, extra_domain)

    def _import_retrieve_and_fill_partner(
        self, invoice, name, phone, mail, vat, country_code=False
    ):
        """Update method to set the partner as a company, not indiovidual"""
        res = super()._import_retrieve_and_fill_partner(
            invoice, name, phone, mail, vat, country_code
        )
        if not invoice.partner_id.is_company and name and vat:
            invoice.partner_id.is_company = True
        return res

    def _import_fill_invoice_form(self, journal, tree, invoice_form, qty_factor):
        def _find_value(xpath, element=tree):
            # avoid 'TypeError: empty namespace prefix is not supported in XPath'
            nsmap = {k: v for k, v in tree.nsmap.items() if k is not None}
            return self.env["account.edi.format"]._find_value(xpath, element, nsmap)

        # Overwrite to take partner from RegistrationName
        if not invoice_form.partner_id:
            role = "Customer" if invoice_form.journal_id.type == "sale" else "Supplier"
            vat = _find_value(
                f"//cac:Accounting{role}Party/cac:Party//cbc:CompanyID", tree
            )
            phone = _find_value(
                f"//cac:Accounting{role}Party/cac:Party//cbc:Telephone", tree
            )
            mail = _find_value(
                f"//cac:Accounting{role}Party/cac:Party//cbc:ElectronicMail", tree
            )
            name = _find_value(
                f"//cac:Accounting{role}Party/cac:Party//cac:PartyLegalEntity//cbc:RegistrationName",  # noqa: B950
                tree,
            )
            country_code = _find_value(
                f"//cac:Accounting{role}Party/cac:Party//cac:Country//cbc:IdentificationCode",
                tree,
            )
            self._import_retrieve_and_fill_partner(
                invoice_form,
                name=name,
                phone=phone,
                mail=mail,
                vat=vat,
                country_code=country_code,
            )
        invoice_form, logs = super()._import_fill_invoice_form(
            journal, tree, invoice_form, qty_factor
        )
        return invoice_form, logs

    def _import_invoice(self, journal, filename, tree, existing_invoice=None):
        invoice = super(AccountEdiXmlCIUSRO, self)._import_invoice(
            journal, filename, tree, existing_invoice=existing_invoice
        )
        if invoice:
            additional_docs = tree.findall("./{*}AdditionalDocumentReference")
            if len(additional_docs) == 0:
                res = self.l10n_ro_renderAnafPdf(invoice)
                if not res:
                    report = self.env.ref(
                        "account.account_invoices_without_payment"
                    ).sudo()
                    pdf = report._render_qweb_pdf(invoice.id)
                    b64_pdf = b64encode(pdf[0])
                    self.l10n_ro_addPDF_from_att(invoice, b64_pdf)
        return invoice

    def l10n_ro_renderAnafPdf(self, invoice):
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", invoice._name), ("res_id", "in", invoice.ids)]
        )
        attachment = attachments.filtered(
            lambda x: f"{invoice.l10n_ro_edi_transaction}.xml" in x.name
        )
        if not attachment:
            return False
        headers = {"Content-Type": "text/plain"}
        xml = b64decode(attachment.datas)
        val1 = "refund" in invoice.move_type and "FCN" or "FACT1"
        val2 = "DA"
        try:
            res = requests.post(
                f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/{val2}",
                data=xml,
                headers=headers,
                timeout=10,
            )
            if "The requested URL was rejected" in res.text:
                xml = xml.replace(
                    b'xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2 ../../UBL-2.1(1)/xsd/maindoc/UBLInvoice-2.1.xsd"',  # noqa: B950
                    "",
                )
                res = requests.post(
                    f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}/{val2}",
                    data=xml,
                    headers=headers,
                    timeout=10,
                )
        except Exception:
            return False
        else:
            return self.l10n_ro_addPDF_from_att(invoice, b64encode(res.content))

    def l10n_ro_addPDF_from_att(self, invoice, pdf):
        attachments = self.env["ir.attachment"].create(
            {
                "name": invoice.ref,
                "res_id": invoice.id,
                "res_model": "account.move",
                "datas": pdf + b"=" * (len(pdf) % 3),  # Fix incorrect padding
                "type": "binary",
                "mimetype": "application/pdf",
            }
        )
        if attachments:
            invoice.with_context(no_new_invoice=True).message_post(
                attachment_ids=attachments.ids
            )
        return True

    def _get_document_allowance_charge_vals_list(self, invoice):
        discount_amount = 0
        for line in invoice.invoice_line_ids:
            if line.discount != 0:
                discount_amount += line.price_unit * line.quantity * line.discount / 100
        if invoice.move_type != "out_invoice" or discount_amount == 0:
            return []

        def grouping_key_generator(tax_values):
            tax = tax_values["tax_id"]
            tax_category_vals = self._get_tax_category_list(invoice, tax)[0]
            grouping_key = {
                "tax_category_id": tax_category_vals["id"],
                "tax_category_percent": tax_category_vals["percent"],
                "_tax_category_vals_": tax_category_vals,
                "tax_amount_type": tax.amount_type,
            }
            if tax.amount_type == "fixed":
                grouping_key["tax_name"] = tax.name
            return grouping_key

        balance_sign = (
            -1
            if invoice.company_id.l10n_ro_credit_note_einvoice
            and invoice.move_type == "out_refund"
            else 1
        )
        taxes_vals = invoice._prepare_edi_tax_details(
            grouping_key_generator=grouping_key_generator,
            filter_to_apply=self._apply_invoice_tax_filter,
            filter_invl_to_apply=self._apply_invoice_line_filter,
        )
        fixed_taxes_keys = [
            k for k in taxes_vals["tax_details"] if k["tax_amount_type"] == "fixed"
        ]
        for key in fixed_taxes_keys:
            fixed_tax_details = taxes_vals["tax_details"].pop(key)
            taxes_vals["tax_amount_currency"] -= fixed_tax_details[
                "tax_amount_currency"
            ]
            taxes_vals["tax_amount"] -= fixed_tax_details["tax_amount"]
            taxes_vals["base_amount_currency"] += fixed_tax_details[
                "tax_amount_currency"
            ]
            taxes_vals["base_amount"] += fixed_tax_details["tax_amount"]
        tax_vals = self._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        tax_category_vals = []
        tax_category_vals.append(
            tax_vals[0]["tax_subtotal_vals"][0]["tax_category_vals"]
        )
        vals = [
            {
                "currency_name": invoice.currency_id.name,
                "currency_dp": invoice.currency_id.decimal_places,
                "charge_indicator": "false",
                "allowance_charge_reason_code": 95,
                "allowance_charge_reason": "Scont",
                "amount": balance_sign * round(discount_amount, 2),
                "tax_category_vals": tax_category_vals,
            }
        ]
        return vals

    def _import_fill_invoice_allowance_charge(
        self, tree, invoice_form, journal, qty_factor
    ):
        logs = []
        if "{urn:oasis:names:specification:ubl:schema:xsd" in tree.tag:
            is_ubl = True
        elif "{urn:un:unece:uncefact:data:standard:" in tree.tag:
            is_ubl = False
        else:
            return

        xpath = (
            "./{*}AllowanceCharge"
            if is_ubl
            else "./{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}SpecifiedTradeAllowanceCharge"  # noqa: B950
        )
        allowance_charge_nodes = tree.findall(xpath)
        for allow_el in allowance_charge_nodes:
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.sequence = (
                    0  # be sure to put these lines above the 'real' invoice lines
                )

                charge_factor = -1  # factor is -1 for discount, 1 for charge
                if is_ubl:
                    charge_indicator_node = allow_el.find("./{*}ChargeIndicator")
                else:
                    charge_indicator_node = allow_el.find(
                        "./{*}ChargeIndicator/{*}Indicator"
                    )
                if charge_indicator_node is not None:
                    charge_factor = -1 if charge_indicator_node.text == "false" else 1
                name = ""
                reason_code_node = allow_el.find(
                    "./{*}AllowanceChargeReasonCode" if is_ubl else "./{*}ReasonCode"
                )
                if reason_code_node is not None:
                    name += reason_code_node.text + " "
                reason_node = allow_el.find(
                    "./{*}AllowanceChargeReason" if is_ubl else "./{*}Reason"
                )
                if reason_node is not None:
                    name += reason_node.text
                invoice_line_form.name = name
                invoice_line_form.account_id = journal.default_account_id

                amount_node = allow_el.find(
                    "./{*}Amount" if is_ubl else "./{*}ActualAmount"
                )
                base_amount_node = allow_el.find(
                    "./{*}BaseAmount" if is_ubl else "./{*}BasisAmount"
                )

                if base_amount_node is not None:
                    invoice_line_form.price_unit = (
                        float(base_amount_node.text) * charge_factor * qty_factor
                    )
                    percent_node = allow_el.find(
                        "./{*}MultiplierFactorNumeric"
                        if is_ubl
                        else "./{*}CalculationPercent"
                    )
                    if percent_node is not None:
                        invoice_line_form.quantity = float(percent_node.text) / 100
                elif amount_node is not None:
                    invoice_line_form.price_unit = (
                        float(amount_node.text) * charge_factor * qty_factor
                    )
                    if charge_factor == -1:
                        invoice_line_form.price_unit = (
                            charge_factor * invoice_line_form.price_unit
                        )
                        invoice_line_form.quantity = (
                            charge_factor * invoice_line_form.quantity
                        )

                invoice_line_form.tax_ids.clear()  # clear the default taxes applied to the line
                tax_xpath = (
                    "./{*}TaxCategory/{*}Percent"
                    if is_ubl
                    else "./{*}CategoryTradeTax/{*}RateApplicablePercent"
                )
                for tax_categ_percent_el in allow_el.findall(tax_xpath):
                    tax = self.env["account.tax"].search(
                        [
                            ("company_id", "=", journal.company_id.id),
                            ("amount", "=", float(tax_categ_percent_el.text)),
                            ("amount_type", "=", "percent"),
                            ("type_tax_use", "=", journal.type),
                        ],
                        limit=1,
                    )
                    if tax:
                        invoice_line_form.tax_ids.add(tax)
                    else:
                        logs.append(
                            _(
                                "Could not retrieve the tax: "
                                "%(tax_percent)s %% for line '%(name)s'.",
                                tax_percent=float(tax_categ_percent_el.text),
                                name=name,
                            )
                        )
        return logs
