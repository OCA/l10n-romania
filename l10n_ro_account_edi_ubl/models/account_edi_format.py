# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests
from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SECTOR_RO_CODES = ("SECTOR1", "SECTOR2", "SECTOR3", "SECTOR4", "SECTOR5", "SECTOR6")


class AccountEdiXmlCIUSRO(models.Model):
    _inherit = "account.edi.format"

    def _export_cius_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        builder = self._get_xml_builder(invoice.company_id)
        xml_content, errors = builder._export_invoice(invoice)
        if errors:
            raise UserError(
                _("The following errors occurred while generating the " "XML file:\n%s")
                % "\n".join(errors)
            )
        xml_content = xml_content.decode()
        xml_content = xml_content.encode()
        xml_name = builder._export_invoice_filename(invoice)
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content,
                "mimetype": "application/xml",
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals["vals"].update(
            {
                "customization_id": "urn:cen.eu:en16931:2017#compliant#"
                "urn:efactura.mfinante.ro:CIUS-RO:1.0.1",
            }
        )
        return vals

    def _get_xml_builder(self, company):
        if self.code == "cius_ro":
            return self.env["account.edi.xml.cius_ro"]
        return super()._get_xml_builder(company)

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._is_compatible_with_journal(journal)
        return journal.type == "sale" and journal.country_code == "RO"

    def _is_required_for_invoice(self, invoice):
        if self.code != "cius_ro":
            return super()._is_required_for_invoice(invoice)
        is_required = invoice.commercial_partner_id.l10n_ro_e_invoice
        if not is_required:
            # Check if it contains high risk products
            invoice_nc_codes = list(
                set(invoice.invoice_line_ids.mapped("product_id.l10n_ro_nc_code"))
            )
            high_risk_nc_codes = invoice.get_l10n_ro_high_risk_nc_codes()
            if invoice_nc_codes and invoice_nc_codes != [False]:
                for hr_code in high_risk_nc_codes:
                    if any(
                        item and item.startswith(hr_code) for item in invoice_nc_codes
                    ):
                        is_required = True
                        break
        return is_required

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            attachment = invoice._get_edi_attachment(self)
            if not attachment:
                attachment = self._export_cius_ro(invoice)
            res[invoice] = {"attachment": attachment, "success": True}
            anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id

            residence = invoice.company_id.l10n_ro_edi_residence
            days = (fields.Date.today() - invoice.invoice_date).days
            if not invoice.company_id.l10n_ro_edi_manual and not anaf_config.state:
                res[invoice] = {
                    "success": False,
                    "error": _("The ANAF configuration is not set"),
                }
            if anaf_config.state != "manual" or (
                invoice.company_id.l10n_ro_edi_manual
                and self.env.context.get("l10n_ro_edi_manual_action")
            ):
                if not invoice.l10n_ro_edi_transaction:
                    if days >= residence:
                        res[invoice] = self._l10n_ro_post_invoice_step_1(
                            invoice, attachment
                        )
                    else:
                        res[invoice] = {
                            "success": False,
                            "error": _("The invoice is not older than %s days")
                            % residence,
                        }

                else:
                    res[invoice] = self._l10n_ro_post_invoice_step_2(invoice)

            if not res[invoice]["success"]:
                body = (
                    _(
                        "The invoice was not sent to ANAF. "
                        "Please check the configuration and try again."
                        "\n\nError: %s"
                    )
                    % res[invoice]["error"]
                )

                invoice.activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=_("e-Invoice not sent to ANAF"),
                    note=body,
                    user_id=invoice.invoice_user_id.id,
                )

        return res

    def _cancel_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._cancel_invoice_edi(invoices)
        return {
            invoice: {"success": False if invoice.l10n_ro_edi_transaction else True}
            for invoice in invoices
        }

    def _needs_web_services(self):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._needs_web_services()
        anaf_config = self.env.company.l10n_ro_account_anaf_sync_id
        return anaf_config.state != "manual"

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii' preluate din Odoo 17.0
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ("supplier", "customer"):
            partner = vals[partner_type]

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

            if not partner.vat and not partner.company_registry:
                constraints[f"ciusro_{partner_type}_tax_identifier_required"] = _(
                    "The following partner doesn't have a VAT nor Company ID: %s. "
                    "At least one of them is required. ",
                    partner.name,
                )

            if partner.vat and not partner.vat.startswith(partner.country_code):
                constraints[f"ciusro_{partner_type}_country_code_vat_required"] = _(
                    "The following partner's doesn't have a "
                    "country code prefix in their VAT: %s.",
                    partner.name,
                )

            if (
                not partner.vat
                and partner.company_registry
                and not partner.company_registry.startswith(partner.country_code)
            ):
                constraints[
                    f"ciusro_{partner_type}_country_code_company_registry_required"
                ] = _(
                    "The following partner's doesn't have a country "
                    "code prefix in their Company ID: %s.",
                    partner.name,
                )

            if (
                partner.country_code == "RO"
                and partner.state_id
                and partner.state_id.code == "B"
                and partner.city not in SECTOR_RO_CODES
            ):
                constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                    "The following partner's city name is invalid: %s. "
                    "If partner's state is București, the city name must be 'SECTORX', "
                    "where X is a number between 1-6.",
                    partner.name,
                )

        return constraints

    def _get_invoice_edi_content(self, move):
        if self.code != "cius_ro":
            return super()._get_invoice_edi_content(move)
        attachment = move._get_edi_attachment(self)
        if not attachment:
            attachment = self._export_cius_ro(move)
            doc = move._get_edi_document(self)
            doc.write({"attachment_id": attachment.id})
        return attachment.raw

    def _l10n_ro_post_invoice_step_1(self, invoice, attachment):

        anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
        access_token = anaf_config.access_token
        url = anaf_config.anaf_einvoice_sync_url + "/upload"
        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        params = {
            "standard": "UBL",
            "cif": invoice.company_id.partner_id.vat.replace("RO", ""),
        }
        response = requests.post(
            url, params=params, data=attachment.raw, headers=headers, timeout=80
        )

        _logger.info(response.content)

        if response.status_code == 200:
            res = {"attachment": attachment}
            doc = etree.fromstring(response.content)
            # header_element = doc.find('header')
            transaction = doc.get("index_incarcare")
            invoice.write({"l10n_ro_edi_transaction": transaction})
        else:
            res = {"success": False, "error": _("Access error")}

        return res

    def _l10n_ro_post_invoice_step_2(self, invoice, test_mode=False):
        anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
        access_token = anaf_config.access_token
        url = anaf_config.anaf_einvoice_sync_url + "/listaMesajeFactura"

        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        params = {
            "zile": 50,
            "cif": invoice.company_id.partner_id.vat.replace("RO", ""),
        }
        response = requests.get(url, params=params, headers=headers, timeout=80)

        _logger.info(response.content)

        url = anaf_config.anaf_einvoice_sync_url + "/stareMesaj"
        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        params = {"id_incarcare": invoice.l10n_ro_edi_transaction}
        response = requests.get(url, params=params, headers=headers, timeout=80)

        _logger.info(response.content)

        if response.status_code == 200:
            res = {"success": True}
            doc = etree.fromstring(response.content)
            stare = doc.get("stare")
            if stare != "ok":
                res = {"success": False}
                if stare == "in prelucrare":
                    res.update({"error": stare, "blocking_level": "info"})
        else:
            res = {"success": False, "error": _("Access error")}

        return res
