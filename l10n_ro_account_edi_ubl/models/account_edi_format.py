# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
        is_required = (
            invoice.commercial_partner_id.country_id.code == "RO"
            and invoice.commercial_partner_id.is_company
        )
        return is_required

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._post_invoice_edi(invoices, test_mode)
        res = {}
        for invoice in invoices:

            anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
            if not anaf_config:
                res[invoice] = {
                    "success": True,
                    "error": _("ANAF sync manual"),
                }
                continue

            attachment = invoice._get_edi_attachment(self)
            if not attachment:
                attachment = self._export_cius_ro(invoice)
            res[invoice] = {"attachment": attachment, "success": True}

            residence = invoice.company_id.l10n_ro_edi_residence
            days = (fields.Date.today() - invoice.invoice_date).days
            if self.env.context.get("l10n_ro_edi_manual_action"):
                if anaf_config and not invoice.l10n_ro_edi_transaction:
                    res[invoice] = self._l10n_ro_post_invoice_step_1(
                        invoice, attachment
                    )
            else:
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
                    res[invoice] = self._l10n_ro_post_invoice_step_2(
                        invoice, attachment
                    )
            if res[invoice].get("error", False):
                invoice.message_post(body=res[invoice]["error"])
                # Create activity if process is stoped with an error blocking level
                if res[invoice].get("blocking_level") == "error":
                    body = (
                        _(
                            "The invoice was not send or validated by ANAF."
                            "\n\nError:"
                            "\n<p>%s</p>"
                        )
                        % res[invoice]["error"]
                    )

                    invoice.activity_schedule(
                        "mail.mail_activity_data_warning",
                        summary=_("The invoice was not send or validated by ANAF"),
                        note=body,
                        user_id=invoice.invoice_user_id.id,
                    )
            # If you have ANAF sync configured, but you don't have a transaction
            # number, then the invoice is marked as not sent to ANAF
            if (
                anaf_config
                and not invoice.l10n_ro_edi_transaction
                and not res.get("transaction")
            ):
                res["success"] = False
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
        return bool(anaf_config)

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
        params = {
            "standard": "UBL" if invoice.move_type == "out_invoice" else "CN",
            "cif": invoice.company_id.partner_id.vat.replace("RO", ""),
        }
        res = self._l10n_ro_anaf_call("/upload", anaf_config, params, attachment.raw)
        if res.get("transaction", False):
            res.update({"attachment": attachment})
            invoice.write({"l10n_ro_edi_transaction": res.get("transaction")})
        return res

    def _l10n_ro_post_invoice_step_2(self, invoice, attachment):
        anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
        params = {"id_incarcare": invoice.l10n_ro_edi_transaction}
        res = self._l10n_ro_anaf_call("/stareMesaj", anaf_config, params, method="GET")
        if res.get("id_descarcare", False):
            invoice.write({"l10n_ro_edi_download": res.get("id_descarcare")})
            if res.get("success", False):
                res.update({"attachment": attachment})
                invoice.message_post(body=_("The invoice was validated by ANAF."))
        return res

    def _l10n_ro_anaf_call(self, func, anaf_config, params, data=None, method="POST"):

        content, status_code = anaf_config._l10n_ro_einvoice_call(
            func, params, data, method
        )
        if status_code == 400:
            error = _("Error %s") % status_code
            return {"success": False, "error": error, "blocking_level": "error"}
        elif status_code != 200:
            return {
                "success": False,
                "error": _("Access Error"),
                "blocking_level": "warning",
            }

        doc = etree.fromstring(content)

        namespaces = {
            "step1": "mfp:anaf:dgti:spv:respUploadFisier:v1",
            "step2": "mfp:anaf:dgti:efactura:stareMesajFactura:v1",
        }
        errors_step1 = doc.find("step1:Errors", namespaces=namespaces)
        error_message_step1 = (
            errors_step1.get("errorMessage") if errors_step1 is not None else None
        )
        errors_step2 = doc.find("step2:Errors", namespaces=namespaces)
        error_message_step2 = (
            errors_step2.get("errorMessage") if errors_step2 is not None else None
        )
        error_message = error_message_step1 or error_message_step2
        if error_message:
            res = {"success": False, "error": error_message, "blocking_level": "error"}
            if "mesaj in cursul zilei" in error_message:
                res.update({"blocking_level": "warning"})
            return res

        # This is response ok from step 1
        transaction = doc.get("index_incarcare", False)
        if transaction:
            return {
                "success": False,
                "transaction": transaction,
                "blocking_level": "info",
                "error": "The invoice was sent to ANAF, awaiting validation.",
            }

        # This is response from step 2
        res = {"success": False}
        stare = doc.get("stare", False)
        stari = {
            "in prelucrare": {
                "success": False,
                "blocking_level": "info",
                "in_processing": True,
                "error": "The invoice is in processing at ANAF.",
            },
            "nok": {
                "success": False,
                "blocking_level": "warning",
                "error": "The invoice was not validated by ANAF.",
            },
            "ok": {"success": True, "id_descarcare": doc.get("id_descarcare") or ""},
            "XML cu erori nepreluat de sistem": {
                "success": False,
                "blocking_level": "error",
                "error": "XML cu erori nepreluat de sistem",
            },
        }
        if stare:
            for key, value in stari.items():
                if key in stare:
                    res.update(value)
                    break
        return res

    def _infer_xml_builder_from_tree(self, tree):
        self.ensure_one()
        customization_id = tree.find("{*}CustomizationID")
        if customization_id is not None:
            if (
                customization_id.text
                == "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
            ):
                return self.env["account.edi.xml.cius_ro"]
        return super()._infer_xml_builder_from_tree(tree)
