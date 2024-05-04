# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Authorization Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/authorize
# Token Issuance Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/token
# Token Revocation Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/revoke
import logging
import secrets
from datetime import datetime, timedelta

import jwt
import requests
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccountANAFSyncWeb(http.Controller):
    @http.route(
        ["/l10n_ro_account_anaf_sync/redirect_anaf/<int:anaf_config_id>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        csrf=False,
    )
    def redirect_anaf(self, anaf_config_id, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        error = False
        if user.share:
            return request.not_found(_("This page is only for internal users!"))
        ANAF_Configs = request.env["l10n.ro.account.anaf.sync"].sudo()
        anaf_config = ANAF_Configs.browse(anaf_config_id)

        if not anaf_config.exists():
            return request.not_found(_("Error, this ANAF config does not exist!"))
        company = anaf_config.company_id
        if not anaf_config.client_id or not anaf_config.client_secret:
            error = (
                f"Error, on ANAF company config {company.name} you does not have a "
                f"Oauth client_id or client_secret for anaf.ro!"
            )

        secret = secrets.token_urlsafe(16)
        now = datetime.now()
        if (
            anaf_config.last_request_datetime
            and anaf_config.last_request_datetime + timedelta(seconds=60) > now
        ):
            error = _("You can make only one request per minute")

        if error:
            values = {"error": error}
            return request.render("l10n_ro_account_anaf_sync.redirect_anaf", values)

        anaf_config.write(
            {
                "response_secret": secret,
                "last_request_datetime": now,
            }
        )
        client_id = anaf_config.client_id
        url = user.get_base_url()
        odoo_oauth_url = f"{url}/l10n_ro_account_anaf_sync/anaf_oauth/{anaf_config.id}"

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": odoo_oauth_url,
            "token_content_type": "jwt",
        }
        redirect_url = anaf_config.anaf_oauth_url + "/authorize?" + url_encode(params)

        anaf_request_from_redirect = request.redirect(
            redirect_url, code=302, local=False
        )

        # This is the default for Authorization Code grant.
        # A successful response is 302 Found which triggers a
        # redirect to the redirect_uri.
        # The response parameters are embedded in the query
        # component (the part after ?)
        # of the redirect_uri in the Location header.
        # For example:
        # HTTP/1.1 302 Found
        # Location: https://my-redirect-uri.callback?code=js89p2x1
        # where the authorization code is js89p21.

        return anaf_request_from_redirect

    @http.route(
        ["/l10n_ro_account_anaf_sync/anaf_oauth/<int:anaf_config_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        csrf=False,
    )
    def get_anaf_oauth_code(self, anaf_config_id, **kw):
        "Returns a text with the result of anaf request from redirect"
        uid = request.uid
        user = request.env["res.users"].browse(uid)

        ANAF_Configs = request.env["l10n.ro.account.anaf.sync"].sudo()
        anaf_config = ANAF_Configs.browse(anaf_config_id)

        if not anaf_config.exists():
            return request.not_found(_("Error, this ANAF config does not exist!"))

        message = ""

        if message:
            anaf_config.message_post(body=message)
            values = {"message": message}
            return request.render("l10n_ro_account_anaf_sync.redirect_anaf", values)

        code = kw.get("code")
        if code:
            headers = {
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "user-agent": "PostmanRuntime/7.29.2",
            }
            url = user.get_base_url()
            redirect_uri = (
                f"{url}/l10n_ro_account_anaf_sync/anaf_oauth/{anaf_config_id}"
            )
            data = {
                "grant_type": "authorization_code",
                "client_id": f"{anaf_config.client_id}",
                "client_secret": f"{anaf_config.client_secret}",
                "code": f"{code}",
                "access_key": f"{code}",
                "redirect_uri": f"{redirect_uri}",
                "token_content_type": "jwt",
            }
            response = requests.post(
                anaf_config.anaf_oauth_url + "/token",
                data=data,
                headers=headers,
                timeout=1.5,
            )
            response_json = response.json()
            access_token = {}
            if response_json.get("access_token", None):
                access_token = jwt.decode(
                    response_json.get("access_token"),
                    algorithms=["RS512"],
                    options={"verify_signature": False},
                )
            message = _("The response was finished.\nResponse was: %s") % response_json
            anaf_config.write(
                {
                    "code": code,
                    "client_token_valability": datetime.fromtimestamp(
                        access_token.get("exp", 0)
                    ),
                    "access_token": response_json.get("access_token", ""),
                    "refresh_token": response_json.get("refresh_token", ""),
                }
            )
        else:
            message = _("No code was found in the response.\nResponse was: %s") % kw

        anaf_config.message_post(body=message)
        values = {"message": message}
        return str(values)
