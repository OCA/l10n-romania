# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

import logging

import requests
from lxml import etree

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    ####################################################
    # Export
    ####################################################

    def _get_cius_ro_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        values.update(
            {
                "customization_id": "urn:cen.eu:en16931:2017"
                "#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0",
            }
        )

        return values

    def _export_cius_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref("l10n_ro_edi_ubl.export_cius_ro_invoice")._render(
            self._get_cius_ro_values(invoice)
        )
        xml_name = "%s.xml" % invoice._get_cius_ro_name()
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content,
                "mimetype": "application/xml",
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )

    #
    # ####################################################
    # # Account.edi.format override
    # ####################################################
    #
    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        if (
            self.code == "cius_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._create_invoice_from_ubl(tree)
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if (
            self.code == "cius_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._update_invoice_from_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    #
    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != "cius_ro" or self._is_account_edi_ubl_cii_available():
            return super()._is_compatible_with_journal(journal)
        return journal.type == "sale" and journal.country_code == "RO"

    def _is_required_for_invoice(self, invoice):
        if self.code != "cus_ro" or self._is_account_edi_ubl_cii_available():
            return super()._is_required_for_invoice(invoice)
        return invoice.commercial_partner_id.l10n_ro_e_invoice

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cius_ro" or self._is_account_edi_ubl_cii_available():
            return super()._post_invoice_edi(invoices, test_mode)
        res = {}
        for invoice in invoices:
            attachment = invoice._get_edi_attachment(self)
            if not attachment:
                attachment = self._export_cius_ro(invoice)
            res[invoice] = {"attachment": attachment}
            if invoice.company_id.l10n_ro_edi_manual and not self.env.context.get(
                "edi_manual_action", False
            ):
                res[invoice] = {
                    "error": _("Automatic transmission is disabled"),
                    "blocking_level": "info",
                    "attachment": attachment,
                }
            else:
                if not invoice.l10n_ro_edi_transaction:
                    res[invoice] = self._l10n_ro_post_invoice_step_1(
                        invoice, attachment, test_mode
                    )
                else:
                    res[invoice] = self._l10n_ro_post_invoice_step_2(invoice, test_mode)

        return res

    def _cancel_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cius_ro" or self._is_account_edi_ubl_cii_available():
            return super()._cancel_invoice_edi(invoices, test_mode)
        return {invoice: {"success": False} for invoice in invoices}

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "cius_ro" or super()._needs_web_services()

    def _l10n_ro_post_invoice_step_1(self, invoice, attachment, test_mode=False):

        access_token = invoice.company_id.l10n_ro_edi_access_token
        if invoice.company_id.l10n_ro_edi_test_mode or test_mode:
            url = "https://api.anaf.ro/test/FCTEL/rest/upload"
        else:
            url = "https://api.anaf.ro/prod/FCTEL/rest/upload"

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

        access_token = invoice.company_id.l10n_ro_edi_access_token
        if invoice.company_id.l10n_ro_edi_test_mode or test_mode:
            url = "https://api.anaf.ro/test/FCTEL/rest/listaMesajeFactura"
        else:
            url = "https://api.anaf.ro/prod/FCTEL/rest/listaMesajeFactura"

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

        access_token = invoice.company_id.l10n_ro_edi_access_token
        if invoice.company_id.l10n_ro_edi_test_mode:
            url = "https://api.anaf.ro/test/FCTEL/rest/stareMesaj"
        else:
            url = "https://api.anaf.ro/prod/FCTEL/rest/stareMesaj"

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

    def _check_move_configuration(self, move):
        self.ensure_one()
        if self.code != "cius_ro" or self._is_account_edi_ubl_cii_available():
            return super()._check_move_configuration(move)
        partner = move.commercial_partner_id
        errors = []
        if not partner.street:
            errors += [_("Partenerul %s nu are completata strada") % partner.name]

        state_bucuresti = self.env.ref("base.RO_B")
        if partner.state_id == state_bucuresti:
            if "sector" not in partner.city.lower():
                errors += [
                    _("localitatea pertenerului %s trebuie sa fie de forma SectorX ")
                    % partner.name
                ]
        return errors

    def _get_invoice_edi_content(self, move):

        if self.code != "cius_ro":
            return super(AccountEdiFormat, self)._get_invoice_edi_content(move)

        attachment = move._get_edi_attachment(self)
        if not attachment:
            attachment = self._export_cius_ro(move)
            doc = move._get_edi_document(self)
            doc.write({"attachment_id": attachment.id})
        return attachment.raw
