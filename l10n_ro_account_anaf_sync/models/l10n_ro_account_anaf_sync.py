# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import timedelta

import jwt
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountANAFSync(models.Model):
    """
    Model representing the synchronization of ANAF
    (National Agency for Fiscal Administration) accounts.

    This model is used to manage the synchronization of ANAF accounts with the Odoo system.
    It provides methods for obtaining access tokens, refreshing tokens, revoking tokens.
    """

    _name = "l10n.ro.account.anaf.sync"
    _inherit = ["mail.thread", "l10n.ro.mixin"]
    _description = "Account ANAF Sync"

    _sql_constraints = [
        (
            "company_id_scope_uniq",
            "unique(company_id, scope)",
            "Another ANAF sync for this company and scope already exists!",
        ),
    ]

    def name_get(self):
        result = []
        for anaf_sync in self:
            result.append((anaf_sync.id, anaf_sync.company_id.name))
        return result

    company_id = fields.Many2one("res.company", required=True)
    anaf_oauth_url = fields.Char(
        default="https://logincert.anaf.ro/anaf-oauth2/v1", readonly=True
    )
    anaf_callback_url = fields.Char(
        compute="_compute_anaf_callback_url",
        help="This is the address to set in anaf_portal_url "
        "(and will work if is https & accessible form internet)",
        readonly=True,
    )
    anaf_redirect_url = fields.Char(
        compute="_compute_anaf_redirect_url",
        help="This is the address that ANAF response will be redirected.",
        readonly=True,
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
        readonly=True,
    )

    access_token = fields.Char(tracking=1, help="Received from ANAF", readonly=True)
    refresh_token = fields.Char(tracking=1, help="Received from ANAF", readonly=True)

    client_token_valability = fields.Date(
        help="Date when is going to expire - 90 days from when was generated",
        tracking=1,
        readonly=True,
    )

    response_secret = fields.Char(
        help="A generated secret to know that the response is ok", readonly=True
    )
    last_request_datetime = fields.Datetime(
        help="Time when was last time pressed the Get Token From Anaf Website."
        " It waits for ANAF request for maximum 1 minute",
        readonly=True,
    )
    scope = fields.Selection(
        [
            ("e-factura", "E-factura"),
            ("e-transport", "E-transport"),
            ("both", "E-factura and E-transport"),
        ],
        default="e-factura",
    )
    token_type = fields.Selection(
        [
            ("opaque", "Opaque"),
            ("jwt", "JWT"),
        ],
        default="opaque",
    )
    anaf_einvoice_sync_url = fields.Char(
        default="https://api.anaf.ro/test/FCTEL/rest", readonly=True
    )
    anaf_etransport_sync_url = fields.Char(
        default="https://api.anaf.ro/test/ETRANSPORT/ws/v1"
    )
    state = fields.Selection(
        [("test", "Test"), ("automatic", "Automatic")],
        default="test",
    )

    @api.onchange("state")
    def _onchange_state(self):
        if self.state:
            if self.state == "test":
                new_url_einvoice = "https://api.anaf.ro/test/FCTEL/rest"
                new_url_etransport = "https://api.anaf.ro/test/ETRANSPORT/ws/v1"
            else:
                new_url_einvoice = "https://api.anaf.ro/prod/FCTEL/rest"
                new_url_etransport = "https://api.anaf.ro/prod/ETRANSPORT/ws/v1"
            self.anaf_einvoice_sync_url = new_url_einvoice
            self.anaf_etransport_sync_url = new_url_etransport

    def _compute_anaf_callback_url(self):
        for anaf_sync in self:
            url = anaf_sync.get_base_url()
            anaf_sync.anaf_callback_url = (
                f"{url}/l10n_ro_account_anaf_sync/anaf_oauth/{anaf_sync.id}"
            )

    def _compute_anaf_redirect_url(self):
        for anaf_sync in self:
            url = anaf_sync.get_base_url()
            anaf_sync.anaf_callback_url = (
                f"{url}/l10n_ro_account_anaf_sync/redirect_anaf/{anaf_sync.id}"
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

    def get_headers_for_anaf_website(self):
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json",
            "user-agent": "PostmanRuntime/7.29.2",
        }
        return headers

    def get_data_for_anaf_website(self, call_type="token"):
        data = {
            "client_id": "{}".format(self.client_id),
            "client_secret": "{}".format(self.client_secret),
            "redirect_uri": "{}".format(self.anaf_redirect_url),
        }
        if self.token_type == "jwt" and call_type == "token":
            data.update(
                {
                    "token_content_type": "jwt",
                }
            )
        if call_type == "token":
            data.update(
                {
                    "grant_type": "authorization_code",
                    "response_type": "code",
                }
            )
        elif call_type == "refresh":
            data.update(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                }
            )
        elif call_type == "revoke":
            data.update(
                {
                    "refresh_token": self.refresh_token,
                }
            )
        return data

    def update_data_from_anaf_website(self, response_data):
        if response_data.get("error"):
            raise UserError(response_data.get("error"))
        valability = fields.Date.today() + timedelta(days=90)
        if "expires_in" in response_data:
            valability = fields.Date.today() + timedelta(
                seconds=response_data.get("expires_in")
            )
        token_data = {
            "access_token": response_data.get("access_token"),
            "refresh_token": response_data.get("refresh_token"),
            "client_token_valability": valability,
            "last_request_datetime": fields.Datetime.now(),
        }
        if "code" in response_data:
            token_data["code"] = response_data.get("code")
        self.write(token_data)

    def handle_anaf_callback(self, anaf_url="authorize", call_type="token"):
        # Folosește codul de autorizare pentru a obține token-ul de acces
        request_url = f"{self.anaf_oauth_url}/{anaf_url}"
        request_headers = self.get_headers_for_anaf_website()
        request_data = self.get_data_for_anaf_website(call_type=call_type)
        try:
            response = requests.post(
                request_url, headers=request_headers, data=request_data, timeout=80
            )
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx

            # If the request was successful, process the response
            if self.token_type == "opaque":
                response_data = response.json()
            else:
                _logger.info(response.content)
                _logger.info(response.text)
                _logger.info(response.jwt)
                payload = jwt.decode(response.jwt, algorithms=["RS512"], verify=False)
                response_data = {
                    "access_token": response.jwt,
                    "refresh_token": payload["refresh_token"],
                    "expires_in": payload["exp"],
                }
                response.json()

            self.update_data_from_anaf_website(response_data)
            self.message_post(
                body=_("The response was finished.\nResponse was: %s" % response_data)
            )
            return response_data

        except requests.exceptions.HTTPError as error_response:
            # Handle HTTP errors
            raise UserError(_("ANAF HTTP Error")) from error_response
        except requests.exceptions.ConnectionError as error_response:
            # Handle connection errors
            raise UserError(_("ANAF Connection Error")) from error_response
        except requests.exceptions.Timeout as error_response:
            # Handle timeout errors
            raise UserError(_("ANAF Timeout Error")) from error_response
        except requests.exceptions.RequestException as error_response:
            # Handle other request errors
            raise UserError(_("ANAF Request Error")) from error_response

    def get_access_token(self):
        self.ensure_one()
        if self.client_id and self.client_secret:
            response_data = self.handle_anaf_callback("authorize")
            return response_data
        return UserError(_("You don't have ANAF code. Please get it first."))

    def refresh_access_token(self):
        self.ensure_one()
        if self.refresh_token:
            response_data = self.handle_anaf_callback("token", call_type="refresh")
            return response_data
        return UserError(_("You don't have ANAF refresh token. Please get it first."))

    def revoke_access_token(self):
        self.ensure_one()
        if self.refresh_token:
            response_data = self.handle_anaf_callback("revoke", call_type="revoke")
            return response_data
        return UserError(_("You don't have ANAF refresh token. Please get it first."))

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

    def _l10n_ro_einvoice_call(self, func, params, data=None, method="POST"):
        self.ensure_one()
        _logger.info("ANAF E-Invoice API call: %s %s" % (func, params))
        url = self.anaf_einvoice_sync_url + func
        content, status_code = self._l10n_ro_anaf_call(url, params, data, method)
        return content, status_code

    def _l10n_ro_etransport_call(self, func, params, data=None, method="POST"):
        self.ensure_one()
        _logger.info("ANAF E-Transport API call: %s %s" % (func, params))
        url = self.anaf_etransport_sync_url + func
        content, status_code = self._l10n_ro_anaf_call(url, params, data, method)
        return content, status_code

    def _l10n_ro_anaf_call(self, url, params, data=None, method="POST"):
        if self.client_token_valability < fields.Date.today():
            _logger.info("ANAF API token expired, refreshing")
            raise UserError(_("Your ANAF API token expired, please refresh it!"))
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
            if response.headers.get("Content-Type", "") == "application/xml":
                _logger.info("ANAF API response: %s" % response.text)
            if "text/plain" in response.headers.get("Content-Type", ""):
                try:
                    content = response.json()
                    if content.get("eroare"):
                        status_code = 400
                except Exception:
                    _logger.info("ANAF API response: %s" % response.text)

        return content, status_code
