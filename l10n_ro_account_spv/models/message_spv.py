# Copyright (C) 2024 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class MessageSPV(models.Model):
    _name = "l10n.ro.message.spv"
    _description = "Message SPV"

    name = fields.Char(string="Message ID")  # id
    cif = fields.Char(string="CIF")  # cif
    message_type = fields.Selection(
        [
            ("in_invoice", "In Invoice"),
            ("out_invoice", "Out Invoice"),
            ("error", "Error"),
        ],
        string="Type",
    )  # tip
    date = fields.Datetime(string="Date")  # data_creare
    details = fields.Char(string="Details")  # detalii
    request_id = fields.Char(string="Request ID")  # id_solicitare

    # campuri suplimentare
    company_id = fields.Many2one("res.company", string="Company")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one("res.partner", string="Partner")

    state = fields.Selection(
        [("draft", "Draft"), ("pending", "Pending"), ("done", "Done")],
        string="State",
        default="draft",
    )

    def get_invoice_from_move(self):
        message_ids = self.mapped("name")
        invoices = self.env["account.move"].search(
            [("l10n_ro_edi_download", "in", message_ids)]
        )
        for message in self:
            invoice = invoices.filtered(
                lambda i: i.l10n_ro_edi_download == message.name
            )
            if invoice:
                message.invoice_id = invoice
                if invoice.edi_state == "sent":
                    message.state = "done"

    def create_invoice(self):
        for message in self:
            if message.message_type == "out_invoice":
                self.get_invoice_from_move()
            if not message.message_type == "in_invoice":
                continue

            move_obj = self.env["account.move"].with_company(message.company_id)
            new_invoice = move_obj.with_context(default_move_type="in_invoice").create(
                {
                    "l10n_ro_edi_download": message.name,
                    "l10n_ro_edi_transaction": message.request_id,
                }
            )
            new_invoice = new_invoice._l10n_ro_prepare_invoice_for_download()
            try:
                new_invoice.l10n_ro_download_zip_anaf(
                    message.company_id._l10n_ro_get_anaf_sync(scope="e-factura")
                )
            except Exception as e:
                new_invoice.message_post(
                    body=_("Error downloading e-invoice: %s") % str(e)
                )

            exist_invoice = move_obj.search(
                [
                    ("ref", "=", new_invoice.ref),
                    ("move_type", "=", "in_invoice"),
                    ("state", "=", "posted"),
                    ("partner_id", "=", new_invoice.partner_id.id),
                    ("id", "!=", new_invoice.id),
                ],
                limit=1,
            )
            if exist_invoice:
                domain = [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", new_invoice.id),
                ]
                attachments = self["ir.attachment"].sudo().search(domain)
                attachments.write({"res_id": exist_invoice.id})
                new_invoice.unlink()
                exist_invoice.write(
                    {
                        "l10n_ro_edi_download": message.name,
                        "l10n_ro_edi_transaction": message.request_id,
                    }
                )
                new_invoice = exist_invoice

            message.write({"invoice_id": new_invoice.id})
