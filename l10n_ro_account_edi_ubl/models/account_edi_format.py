# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests
from lxml import etree

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountEdiXmlCIUSRO(models.Model):
    _inherit = "account.edi.format"

    def _export_cius_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        builder = self._get_xml_builder(invoice.company_id)
        xml_content, errors = builder._export_invoice(invoice)
        xml_content = xml_content.decode()
        xml_content = xml_content.replace("CreditNoteLine", "InvoiceLine")
        xml_content = xml_content.replace("CreditedQuantity", "InvoicedQuantity")
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
                "urn:efactura.mfinante.ro:CIUS-RO:1.0.0",
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

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._post_invoice_edi(invoices, test_mode)
        res = {}
        for invoice in invoices:
            attachment = invoice._get_edi_attachment(self)
            if not attachment:
                attachment = self._export_cius_ro(invoice)
            res[invoice] = {"attachment": attachment, "success": True}
            anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
            if anaf_config.state != "manual" and (
                invoice.company_id.l10n_ro_edi_manual
                and self.env.context.get("l10n_ro_edi_manual_action")
            ):
                if not invoice.l10n_ro_edi_transaction:
                    res[invoice] = self._l10n_ro_post_invoice_step_1(
                        invoice, attachment
                    )
                else:
                    res[invoice] = self._l10n_ro_post_invoice_step_2(invoice)

        return res

    def _cancel_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._cancel_invoice_edi(invoices, test_mode)
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

    def _check_move_configuration(self, move):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._check_move_configuration(move)
        partner = move.commercial_partner_id
        errors = []
        if not partner.street:
            errors += [
                _("The partner doesn't have the street completed.") % partner.name
            ]

        state_bucuresti = self.env.ref("base.RO_B")
        if partner.state_id == state_bucuresti:
            if "sector" not in partner.city.lower():
                errors += [
                    _(
                        "If country state of partner %s is Bucharest, "
                        "the city must be as SectorX "
                    )
                    % partner.name
                ]
        return errors

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
        response = requests.get(url, params=params, headers=headers)

        _logger.info(response.content)

        url = anaf_config.anaf_einvoice_sync_url + "/stareMesaj"
        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        params = {"id_incarcare": invoice.l10n_ro_edi_transaction}
        response = requests.get(url, params=params, headers=headers)

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
