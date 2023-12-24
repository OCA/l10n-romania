# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


ONBOARDING_STEP_STATES = [
    ("not_done", "Not done"),
    ("just_done", "Just done"),
    ("done", "Done"),
]
DASHBOARD_ONBOARDING_STATES = ONBOARDING_STEP_STATES + [("closed", "Closed")]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_edi_residence = fields.Integer(string="Period of Residence", default=5)
    l10n_ro_edi_cius_embed_pdf = fields.Boolean(
        string="Embed PDF in CIUS", default=False
    )
    l10n_ro_default_cius_pdf_report = fields.Many2one(
        "ir.actions.report",
        string="Default PDF Report",
        help="Default PDF report to be attached to xml e-invoice.",
    )
    l10n_ro_download_einvoices = fields.Boolean(
        string="Download e-invoices from ANAF", default=False
    )
    l10n_ro_download_einvoices_start_date = fields.Date(
        string="Start date to download e-invoices"
    )
    l10n_ro_download_einvoices_days = fields.Integer(
        string="Maximum number of days to download e-invoices.", default=10
    )
    l10n_ro_anaf_edi_cron_result = fields.Text()
    l10n_ro_token_status_data_state_step = fields.Selection(
        ONBOARDING_STEP_STATES,
        string="State of the onboarding anaf sycn status",
        default="not_done",
    )
    l10n_ro_edi_download_cron_data_state_step = fields.Selection(
        ONBOARDING_STEP_STATES,
        string="State of the onboarding anaf edi download cron step",
        default="not_done",
    )
    l10n_ro_anaf_edi_onboarding_state = fields.Selection(
        DASHBOARD_ONBOARDING_STATES,
        string="State of the edi ubl dashboard onboarding panel",
        default="not_done",
    )

    @api.constrains("l10n_ro_edi_residence", "l10n_ro_download_einvoices_days")
    def _check_l10n_ro_edi_residence(self):
        for company in self:
            if company.l10n_ro_edi_residence < 0 or company.l10n_ro_edi_residence > 5:
                raise models.ValidationError(
                    _("The period of residence must be between 0 and 5.")
                )
            if (
                company.l10n_ro_download_einvoices_days < 0
                or company.l10n_ro_download_einvoices_days > 60
            ):
                raise models.ValidationError(
                    _(
                        "The maximum number of days to download e-invoices "
                        "must be between 0 and 60."
                    )
                )

    def _l10n_ro_get_anaf_efactura_messages(self):
        company_messages = []
        anaf_config = self.get_l10n_ro_anaf_sync("e-invoice")
        if not anaf_config:
            _logger.warning("No ANAF configuration for company %s", self.name)
            return company_messages
        if not anaf_config.access_token:
            _logger.warning("No access token for company %s", self.name)
            return company_messages
        no_days = self.l10n_ro_download_einvoices_days or "60"
        params = {
            "zile": no_days,
            "cif": self.partner_id.l10n_ro_vat_number,
        }
        content, status_code = anaf_config._l10n_ro_einvoice_call(
            "/listaMesajeFactura", params, method="GET"
        )
        if status_code == 200:
            doc = json.loads(content.decode("utf-8"))
            company_messages = list(
                filter(
                    lambda m: m.get("cif") == self.partner_id.l10n_ro_vat_number
                    and m.get("tip") == "FACTURA PRIMITA",
                    doc.get("mesaje") or [],
                )
            )
        return company_messages

    @api.model
    def _l10n_ro_create_anaf_efactura(self):
        # method to be used in cron job to auto download e-invoices from ANAF
        ro_companies = self.search([]).filtered(
            lambda c: c.country_id.code == "RO"
            and c.get_l10n_ro_anaf_sync("e-invoice")
            and c.l10n_ro_download_einvoices
        )
        ro_companies.l10n_ro_anaf_edi_cron_result = False
        for company in ro_companies:
            try:
                move_obj = self.env["account.move"].with_company(company)
                company_messages = company._l10n_ro_get_anaf_efactura_messages()

                for message in company_messages:
                    if company.l10n_ro_download_einvoices_start_date:
                        if message.get("data_creare"):
                            message_date = datetime.strptime(
                                message.get("data_creare")[:8], "%Y%m%d"
                            ).strftime(DATE_FORMAT)
                            if (
                                fields.Date.from_string(message_date)
                                < company.l10n_ro_download_einvoices_start_date
                            ):
                                continue
                    invoice = move_obj.search(
                        [("l10n_ro_edi_download", "=", message.get("id"))]
                    )
                    if not invoice:
                        new_invoice = move_obj.with_context(
                            default_move_type="in_invoice"
                        ).create(
                            {
                                "l10n_ro_edi_download": message.get("id"),
                                "l10n_ro_edi_transaction": message.get("id_solicitare"),
                            }
                        )
                        new_invoice.l10n_ro_download_zip_anaf(
                            company.get_l10n_ro_anaf_sync("e-invoice")
                        )
            except Exception as e:
                _logger.error(
                    "Error while downloading e-invoices from ANAF: %s", str(e)
                )
                company.l10n_ro_anaf_edi_cron_result = str(e)

    def get_and_update_l10n_ro_anaf_edi_onboarding_state(self):
        """This method is called on the controller rendering method
        and ensures that the animations are displayed only one time."""
        self.l10n_ro_token_status_data_state_step = "not_done"
        self.l10n_ro_edi_download_cron_data_state_step = "not_done"
        if not self.l10n_ro_anaf_edi_cron_result:
            self.l10n_ro_edi_download_cron_data_state_step = "done"
        if self.get_l10n_ro_anaf_sync("e-invoice"):
            token_date = self.get_l10n_ro_anaf_sync("e-invoice").client_token_valability
            if (token_date - fields.Date.today()).days > 5:
                self.l10n_ro_token_status_data_state_step = "done"

        result = self._get_and_update_onboarding_state(
            "l10n_ro_anaf_edi_onboarding_state",
            self.get_account_edi_ubl_dashboard_onboarding_steps_states_names(),
        )
        return result

    def get_account_edi_ubl_dashboard_onboarding_steps_states_names(self):
        return [
            "l10n_ro_token_status_data_state_step",
            "l10n_ro_edi_download_cron_data_state_step",
        ]

    @api.model
    def action_close_l10n_ro_anaf_edi_onboarding(self):
        """Mark the dashboard onboarding panel as closed."""
        self.env.company.l10n_ro_anaf_edi_onboarding_state = "closed"

    @api.model
    def action_open_l10n_ro_anaf_sync_onboarding(self):
        """Onboarding step ANAF Sync status."""
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_account_anaf_sync.action_account_anaf_sync"
        )
        action["res_id"] = self.env.company.get_l10n_ro_anaf_sync("e-invoice").id
        return action
