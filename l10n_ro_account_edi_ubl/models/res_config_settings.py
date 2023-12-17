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

    l10n_ro_download_einvoices = fields.Boolean(
        related="company_id.l10n_ro_download_einvoices",
        readonly=False,
        string="Download e-invoices from ANAF",
    )
