# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_edi_residence = fields.Integer(
        related="company_id.l10n_ro_edi_residence",
        readonly=False,
        string="Residence",
    )

    l10n_ro_edi_cius_embed_pdf = fields.Boolean(
        related="company_id.l10n_ro_edi_cius_embed_pdf",
        readonly=False,
        string="Embed PDF in CIUS",
    )
    l10n_ro_default_cius_pdf_report = fields.Many2one(
        related="company_id.l10n_ro_default_cius_pdf_report",
        readonly=False,
        string="Default PDF Report",
        help="Default PDF report to be attached to xml e-invoice.",
    )

    l10n_ro_download_einvoices = fields.Boolean(
        related="company_id.l10n_ro_download_einvoices",
        readonly=False,
        string="Download e-invoices from ANAF",
    )
    l10n_ro_download_einvoices_start_date = fields.Date(
        related="company_id.l10n_ro_download_einvoices_start_date",
        readonly=False,
        string="Start date to download e-invoices",
    )
    l10n_ro_download_einvoices_days = fields.Integer(
        related="company_id.l10n_ro_download_einvoices_days",
        readonly=False,
        string="Maximum number of days to download e-invoices.",
    )
    l10n_ro_store_einvoices = fields.Boolean(
        related="company_id.l10n_ro_store_einvoices",
        readonly=False,
        string="Store E-Invoice signed by Anaf.",
    )
    l10n_ro_credit_note_einvoice = fields.Boolean(
        related="company_id.l10n_ro_credit_note_einvoice",
        readonly=False,
        string="Credit Note on e-invoice.",
    )
    l10n_ro_render_anaf_pdf = fields.Boolean(
        related="company_id.l10n_ro_render_anaf_pdf",
        readonly=False,
        string="Render Anaf PDF",
    )
    l10n_ro_edi_error_notify_users = fields.Many2many(
        related="company_id.l10n_ro_edi_error_notify_users",
        readonly=False,
        string="EDI Error Notify Users",
    )
