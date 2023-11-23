# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import timedelta

import requests
from werkzeug.urls import url_encode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountANAFSync(models.Model):
    _name = "l10n.ro.account.anaf.sync"
    _inherit = ["mail.thread", "l10n.ro.mixin"]
    _description = "Account ANAF Sync"

    _sql_constraints = [
        (
            "company_id_uniq",
            "unique(company_id)",
            "Another ANAF sync for this company already exists!",
        ),
    ]

    def name_get(self):
        result = []
        for anaf_sync in self:
            result.append((anaf_sync.id, anaf_sync.company_id.name))
        return result

    company_id = fields.Many2one("res.company", required=True)
    anaf_oauth_url = fields.Char(default="https://logincert.anaf.ro/anaf-oauth2/v1")
    anaf_callback_url = fields.Char(
        compute="_compute_anaf_callback_url",
        help="This is the address to set in anaf_portal_url "
        "(and will work if is https & accessible form internet)",
    )
    client_id = fields.Char(
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
    )
    client_secret = fields.Char(
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
    )
    code = fields.Char(
        help="Received from ANAF with this you can take access token and refresh_token",
        tracking=1,
    )

    access_token = fields.Char(tracking=1, help="Received from ANAF")
    refresh_token = fields.Char(tracking=1, help="Received from ANAF")

    client_token_valability = fields.Date(
        help="Date when is going to expire - 90 days from when was generated",
        tracking=1,
    )

    response_secret = fields.Char(
        help="A generated secret to know that the response is ok"
    )
    last_request_datetime = fields.Datetime(
        help="Time when was last time pressed the Get Token From Anaf Website."
        " It waits for ANAF request for maximum 1 minute",
    )
    anaf_einvoice_sync_url = fields.Char(default="https://api.anaf.ro/test/FCTEL/rest")
    state = fields.Selection(
        [("test", "Test"), ("manual", "Manual"), ("automatic", "Automatic")],
        default="test",
    )

    def write(self, values):
        if values.get("company_id"):
            company = self.env["res.company"].browse(values["company_id"])
            for record in self:
                if record.company_id and record.company_id != company:
                    raise UserError(
                        _(
                            "You cannot change the company."
                            "Please delete the config and create another one."
                        )
                    )
            if company and len(self) == 1:
                company.l10n_ro_account_anaf_sync_id = self
        return super().write(values)

    def _compute_anaf_callback_url(self):
        for anaf_sync in self:
            url = anaf_sync.get_base_url()
            anaf_sync.anaf_callback_url = (
                f"{url}/l10n_ro_account_anaf_sync/anaf_oauth/{anaf_sync.id}"
            )

    def get_token_from_anaf_website(self):
        self.ensure_one()
        if self.access_token:
            raise UserError(
                _("You already have an ANAF access token. Please revoke it first.")
            )

        # Construiește URL-ul de autorizare
        param = {
            "anaf_oauth_url": self.anaf_oauth_url,
            "client_id": self.client_id,
            "redirect_uri": self.anaf_callback_url,
            "response_type": "code",
        }

        authorization_url = f"{self.anaf_oauth_url}/authorize?{url_encode(param)}"

        # Redirectează utilizatorul către URL-ul de autorizare
        return {
            "type": "ir.actions.act_url",
            "url": authorization_url,
            "target": "new",
        }

    def handle_anaf_callback(self, authorization_code):
        # Folosește codul de autorizare pentru a obține token-ul de acces
        token_url = f"{self.anaf_oauth_url}/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.anaf_callback_url,
        }

        response = requests.post(
            token_url,
            data=data,
            timeout=80,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            # Extrage token-ul de acces din răspunsul JSON
            token_data = response.json()
            self.write(
                {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "client_token_valability": fields.Date.today()
                    + timedelta(days=90),  # Valabilitate de 90 de zile
                    "last_request_datetime": fields.Datetime.now(),
                }
            )

    def revoke_access_token(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("You don't have ANAF access token. Please get it first."))
        param = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            # "refresh_token": should function for refresh function
            "token_type_hint": "access_token",  # refresh_token  (should work without)
        }
        url = self.anaf_oauth_url + "/revoke"
        response = requests.post(
            url,
            data=param,
            timeout=80,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if response.status_code == 200:
            message = _("Revoke token response: %s") % response.json()
        else:
            message = _("Revoke token response: %s") % response.reason
        self.message_post(body=message)
        if response.status_code == 200:
            self.write(
                {
                    "code": "",
                    "access_token": "",
                    "refresh_token": "",
                    "last_request_datetime": False,
                    "client_token_valability": False,
                }
            )

    def test_anaf_api(self):
        self.ensure_one()
        url = "https://api.anaf.ro/TestOauth/jaxrs/hello?name=test_from_odoo"

        response = requests.get(
            url,
            data={"name": "test_anaf"},
            headers={
                "Content-Type": "multipart/form-data",
                "Authorization": f"Bearer {self.access_token}",
            },
            timeout=80,
        )
        if response.status_code == 200:
            message = _("Test token response: %s") % response.json()
        else:
            message = _("Test token response: %s") % response.reason
        self.message_post(body=message)

    @api.onchange("state")
    def _onchange_state(self):
        if self.state:
            if self.state in ("test", "manual"):
                new_url = "https://api.anaf.ro/test/FCTEL/rest"
            else:
                new_url = "https://api.anaf.ro/prod/FCTEL/rest"
            self.anaf_einvoice_sync_url = new_url

    def _l10n_ro_einvoice_call(self, func, params, data=None, method="POST"):
        self.ensure_one()
        _logger.info("ANAF API call: %s %s" % (func, params))
        url = self.anaf_einvoice_sync_url + func
        access_token = self.access_token
        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        test_data = self.env.context.get("test_data", False)
        if test_data:
            content = test_data
            status_code = 200
        else:
            if method == "GET":
                response = requests.get(
                    url, params=params, data=data, headers=headers, timeout=80
                )
            else:
                response = requests.post(
                    url, params=params, data=data, headers=headers, timeout=80
                )

            content = response.content
            status_code = response.status_code
            if response.status_code == 400:
                content = response.json()
            if response.headers.get("Content-Type") == "application/xml":
                _logger.info("ANAF API response: %s" % response.text)
            if "text/plain" in response.headers.get("Content-Type"):
                try:
                    content = response.json()
                    if content.get("eroare"):
                        status_code = 400
                except Exception:
                    _logger.info("ANAF API response: %s" % response.text)

        return content, status_code
