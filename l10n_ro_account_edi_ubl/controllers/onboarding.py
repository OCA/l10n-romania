from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):
    @http.route(
        "/l10n_ro_account_edi_ubl/account_dashboard_onboarding",
        auth="user",
        type="json",
    )
    def account_dashboard_onboarding(self):
        """Returns the `banner` for the account dashboard onboarding panel.
        It will show information about the company ANAF token validity and
        errors from ANAF download invoices cron job"""
        company = request.env.company
        status = company.get_and_update_l10n_ro_anaf_edi_onboarding_state()
        if (
            company.l10n_ro_token_status_data_state_step == "done"
            and company.l10n_ro_edi_download_cron_data_state_step == "done"
        ):
            company.l10n_ro_anaf_edi_onboarding_state = "closed"
        else:
            company.l10n_ro_anaf_edi_onboarding_state = "not_done"
        if company.l10n_ro_anaf_edi_onboarding_state == "closed":
            return {}

        return {
            "html": request.env["ir.qweb"]._render(
                "l10n_ro_account_edi_ubl.account_dashboard_edi_ubl_onboarding_panel",
                {"company": company, "state": status},
            )
        }
