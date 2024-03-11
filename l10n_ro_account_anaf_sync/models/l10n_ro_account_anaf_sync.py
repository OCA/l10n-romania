# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

import jwt
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountANAFSync(models.Model):
    _name = "l10n.ro.account.anaf.sync"
    _inherit = ["mail.thread", "l10n.ro.mixin"]
    _description = "Account ANAF Sync"

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
    state = fields.Selection(
        [("test", "Test"), ("automatic", "Automatic")],
        default="test",
    )
    anaf_scope_ids = fields.One2many(
        comodel_name="l10n.ro.account.anaf.sync.scope", inverse_name="anaf_sync_id"
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
        return_url = "/l10n_ro_account_anaf_sync/redirect_anaf/%s" % self.id
        return {
            "type": "ir.actions.act_url",
            "url": "%s" % return_url,
            "target": "new",
        }

    def _anaf_call_update_token(self, response):
        # Extrage token-ul de acces din răspunsul JSON
        token_data = response.json()
        acces_token = {}
        if token_data.get("access_token", None):
            acces_token = jwt.decode(
                token_data.get("access_token"),
                algorithms=["RS512"],
                options={"verify_signature": False},
            )
        vals = {}
        if token_data.get("access_token"):
            vals["access_token"] = token_data.get("access_token")
        if token_data.get("refresh_token"):
            vals["refresh_token"] = token_data.get("refresh_token")
        if acces_token.get("exp"):
            vals["client_token_valability"] = datetime.fromtimestamp(
                acces_token.get("exp", 0)
            )
        vals["last_request_datetime"] = fields.Datetime.now()
        self.write(vals)

    def handle_anaf_callback(self, authorization_code):
        # Folosește codul de autorizare pentru a obține token-ul de acces
        token_url = f"{self.anaf_oauth_url}/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.anaf_callback_url,
            "token_content_type": "jwt",
        }

        response = requests.post(
            token_url,
            data=data,
            timeout=80,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            self._anaf_call_update_token(response)

    def refresh_access_token(self):
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(
                _("You don't have ANAF refresh token. Please get it first.")
            )
        token_url = f"{self.anaf_oauth_url}/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = requests.post(
            token_url,
            data=data,
            timeout=80,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            self._anaf_call_update_token(response)

    def revoke_access_token(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("You don't have ANAF access token. Please get it first."))
        param = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
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
