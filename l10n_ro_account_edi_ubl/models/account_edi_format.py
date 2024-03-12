# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from lxml import etree

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountEdiXmlCIUSRO(models.Model):
    _inherit = "account.edi.format"

    def _export_cius_ro(self, invoice):
        self.ensure_one()
        # Create file content.
        res = self.env["ir.attachment"]
        if not invoice.l10n_ro_edi_transaction:
            edi_document = invoice.edi_document_ids.filtered(
                lambda l: l.edi_format_id.code == "cius_ro"
            )
            if edi_document:
                builder = self._get_xml_builder(invoice.company_id)
                xml_content, errors = builder._export_invoice(invoice)
                if errors:
                    return errors
                xml_content = xml_content.decode()
                xml_content = xml_content.encode()
                xml_name = builder._export_invoice_filename(invoice)
                old_attachment = edi_document.attachment_id
                if old_attachment:
                    edi_document.attachment_id = False
                    old_attachment.unlink()
                res = self.env["ir.attachment"].create(
                    {
                        "name": xml_name,
                        "raw": xml_content,
                        "mimetype": "application/xml",
                        "res_model": "account.move",
                        "res_id": invoice.id,
                    }
                )
            else:
                return res
        else:
            res = invoice._get_edi_attachment(self)
        return res

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _find_value(self, xpath, xml_element, namespaces=None):
        res = None
        try:
            res = super(AccountEdiXmlCIUSRO, self)._find_value(
                xpath, xml_element, namespaces=namespaces
            )
        except Exception:
            namespaces = {
                "qdt": "urn:oasis:names:specification:ubl:schema:xsd:QualifiedDataTypes-2",
                "ccts": "urn:un:unece:uncefact:documentation:2",
                "udt": "urn:oasis:names:specification:ubl:schema:xsd:UnqualifiedDataTypes-2",
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",  # noqa: B950
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            }
            res = super(AccountEdiXmlCIUSRO, self)._find_value(
                xpath, xml_element, namespaces=namespaces
            )
        return res

    def _get_xml_builder(self, company):
        if self.code == "cius_ro":
            return self.env["account.edi.xml.cius_ro"]
        return super()._get_xml_builder(company)

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._is_compatible_with_journal(journal)
        return journal.type == "sale" and journal.country_code == "RO"

    def _get_move_applicability(self, move):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._get_move_applicability(move)
        if self.code == "cius_ro" and self._is_required_for_invoice(move):
            return {
                "post": self._post_invoice_edi,
                "cancel": self._cancel_invoice_edi,
                "edi_content": self._get_invoice_edi_content,
            }
        return False

    def _is_required_for_invoice(self, invoice):
        if self.code != "cius_ro":
            return super()._is_required_for_invoice(invoice)
        is_required = (
            invoice.move_type in ("out_invoice", "out_refund")
            and invoice.commercial_partner_id.country_id.code == "RO"
            and invoice.commercial_partner_id.is_company
        )
        return is_required

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != "cius_ro":
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            anaf_config = invoice.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
            if not anaf_config:
                res[invoice] = {
                    "success": True,
                    "error": _("ANAF sync manual"),
                }
                continue

            attachment = invoice._get_edi_attachment(self)
            if not attachment:
                attachment = self._export_cius_ro(invoice)
            # In case of error, the attachment is a list of string
            if not isinstance(attachment, models.Model):
                res[invoice] = {
                    "success": False,
                    "error": attachment,
                    "blocking_level": "warning",
                }
                invoice.message_post(body=res[invoice]["error"])
                message = _("There are some errors when generating the XMl file.")
                body = message + _("\n\nError:\n<p>%s</p>") % res[invoice]["error"]
                invoice.activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=message,
                    note=body,
                    user_id=invoice.invoice_user_id.id,
                )
                continue
            res[invoice] = {"attachment": attachment, "success": True}

            residence = invoice.company_id.l10n_ro_edi_residence or 0
            days = (fields.Date.today() - invoice.invoice_date).days
            if not invoice.l10n_ro_edi_transaction:
                should_send = days >= residence or self.env.context.get(
                    "l10n_ro_edi_manual_action"
                )
                if should_send:
                    try:
                        res[invoice] = self._l10n_ro_post_invoice_step_1(
                            invoice, attachment
                        )
                    except Exception as e:
                        res[invoice] = {
                            "success": False,
                            "error": str(e),
                            "blocking_level": "info",
                        }
                else:
                    res[invoice]["success"] = False
                    continue
            else:
                res[invoice] = self._l10n_ro_post_invoice_step_2(invoice, attachment)
            if res[invoice].get("error", False):
                invoice.message_post(body=res[invoice]["error"])
                # Create activity if process is stopped with an error blocking level
                if res[invoice].get("blocking_level") == "error":
                    message = _("The invoice was not send or validated by ANAF.")
                    body = message + _("\n\nError:\n<p>%s</p>") % res[invoice]["error"]
                    invoice.activity_schedule(
                        "mail.mail_activity_data_warning",
                        summary=message,
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
                res[invoice]["success"] = False
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
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-factura")
        return bool(anaf_config)

    def _get_invoice_edi_content(self, move):
        if self.code != "cius_ro":
            return super()._get_invoice_edi_content(move)
        attachment = move._get_edi_attachment(self)
        if not attachment:
            attachment = self._export_cius_ro(move)
        doc = move._get_edi_document(self)
        # In case of error, the attachment is a list of string
        if not isinstance(attachment, models.Model):
            doc.write({"error": attachment, "blocking_level": "warning"})
            move.message_post(body=attachment)
            message = _("There are some errors when generating the XMl file.")
            body = message + _("\n\nError:\n<p>%s</p>") % attachment
            move.activity_schedule(
                "mail.mail_activity_data_warning",
                summary=message,
                note=body,
                user_id=move.invoice_user_id.id,
            )
            return b""
        else:
            doc.write({"attachment_id": attachment.id})
            return attachment.raw

    def _l10n_ro_post_invoice_step_1(self, invoice, attachment):
        anaf_config = invoice.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
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
        anaf_config = invoice.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
        params = {"id_incarcare": invoice.l10n_ro_edi_transaction}
        res = self._l10n_ro_anaf_call("/stareMesaj", anaf_config, params, method="GET")
        if res.get("id_descarcare", False):
            invoice.write({"l10n_ro_edi_download": res.get("id_descarcare")})
            if res.get("success", False):
                res.update({"attachment": attachment})
                invoice.message_post(body=_("The invoice was validated by ANAF."))
                if invoice.company_id.l10n_ro_store_einvoices:
                    invoice.l10n_ro_download_zip_anaf()
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
                "error": _("The invoice was sent to ANAF, awaiting validation."),
            }

        # This is response from step 2
        res = {"success": False}
        stare = doc.get("stare", False)
        stari = {
            "in prelucrare": {
                "success": False,
                "blocking_level": "info",
                "in_processing": True,
                "error": _("The invoice is in processing at ANAF."),
            },
            "nok": {
                "success": False,
                "blocking_level": "warning",
                "error": _("The invoice was not validated by ANAF."),
            },
            "ok": {"success": True, "id_descarcare": doc.get("id_descarcare") or ""},
            "XML cu erori nepreluat de sistem": {
                "success": False,
                "blocking_level": "error",
                "error": _("XML with errors not taken over by the system."),
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
