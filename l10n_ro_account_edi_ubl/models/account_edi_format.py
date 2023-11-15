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
            if not invoice.company_id.l10n_ro_edi_manual and not anaf_config:
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

            if res[invoice].get("error", False):
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

    def _l10n_ro_post_invoice_step_2(self, invoice):
        anaf_config = invoice.company_id.l10n_ro_account_anaf_sync_id
        params = {"id_incarcare": invoice.l10n_ro_edi_transaction}
        res = self._l10n_ro_anaf_call("/stareMesaj", anaf_config, params, method="GET")
        if res.get("id_descarcare", False):
            invoice.write({"l10n_ro_edi_download": res.get("id_descarcare")})
        if res.get("in_processing"):
            invoice.message_post(
                body=_(
                    "ANAF Validation for %s is in processing.",
                    invoice.l10n_ro_edi_transaction,
                )
            )
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
        execution_status = doc.get("ExecutionStatus", "0")
        if execution_status == "1":
            error = doc.find(".//").get("errorMessage")
            return {"success": False, "error": error}
        transaction = doc.get("index_incarcare", False)
        if transaction:
            return {
                "success": False,
                "transaction": transaction,
                "blocking_level": "info",
            }

        res = {"success": True}
        stare = doc.get("stare", False)
        if stare == "in prelucrare":
            res.update(
                {"success": False, "blocking_level": "info", "in_processing": True}
            )
        elif stare == "nok":
            res.update({"success": False, "blocking_level": "error"})
        id_descarcare = doc.get("id_descarcare")
        res.update({"id_descarcare": id_descarcare})

        return res
