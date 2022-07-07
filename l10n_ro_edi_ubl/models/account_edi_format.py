# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

import logging

import markupsafe
import requests
from lxml import etree

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    ####################################################
    # Export
    ####################################################

    def _get_cirus_ro_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        values.update(
            {
                "customization_id": "urn:cen.eu:en16931:2017"
                "#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0",
            }
        )

        return values

    def _export_cirus_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env.ref("l10n_ro_edi_ubl.export_cirus_ro_invoice")._render(
            self._get_cirus_ro_values(invoice)
        )
        xml_name = "%s.xml" % invoice._get_cirus_ro_name()
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_content.encode(),
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
            self.code == "cirus_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._create_invoice_from_ubl(tree)
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if (
            self.code == "cirus_ro"
            and self._is_ubl(filename, tree)
            and not self._is_account_edi_ubl_cii_available()
        ):
            return self._update_invoice_from_ubl(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    #
    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != "cirus_ro" or self._is_account_edi_ubl_cii_available():
            return super()._is_compatible_with_journal(journal)
        return journal.type == "sale" and journal.country_code == "RO"

    #
    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != "cirus_ro" or self._is_account_edi_ubl_cii_available():
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            if not invoice.l10n_ro_edi_transaction:
                res[invoice] = self._l10n_ro_post_invoice_step_1(invoice)
            else:
                res[invoice] = self._l10n_ro_post_invoice_step_2(invoice)

        return res

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "cirus_ro" or super()._needs_web_services()

    def _l10n_ro_post_invoice_step_1(self, invoice):
        attachment = self._export_cirus_ro(invoice)
        access_token = invoice.company_id.l10n_ro_edi_token
        if invoice.company_id.l10n_ro_edi_test_mode:
            url = "https://api.anaf.ro/test/FCTEL/rest/upload?standard=UBL"
        else:
            url = "https://api.anaf.ro/prod/FCTEL/rest/upload?standard=UBL"

        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }

        response = requests.post(url, data=attachment.raw, headers=headers, timeout=80)

        _logger.info(response.content)

        if response.status_code == "200":
            res = {"attachment": attachment}
            doc = etree.fromstring(response.content)
            # header_element = doc.find('header')
            transaction = doc.get("index_incarcare")
            invoice.write({"l10n_ro_edi_transaction": transaction})
        else:
            res = {"success": False, "error": _("Access error")}

        return res

    def _l10n_ro_post_invoice_step_2(self, invoice):

        access_token = invoice.company_id.l10n_ro_edi_token
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

        if response.status_code == "200":
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
