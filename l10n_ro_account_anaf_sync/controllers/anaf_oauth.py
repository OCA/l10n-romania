# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import secrets
from datetime import datetime, timedelta

import requests

from odoo import _, http
from odoo.http import request

# Authorization Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/authorize
# Token Issuance Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/token
# Token Revocation Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/revoke


class AccountANAFSyncWeb(http.Controller):
    @http.route(
        ["/l10n_ro_account_anaf_sync/redirect_anaf/<int:anaf_config_id>"],
        type="http",
        auth="user",
        website=False,
        sitemap=False,
    )
    def redirect_anaf(self, anaf_config_id, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        error = False
        if user.share:
            return request.not_found(_("This page is only for internal users!"))
        anaf_config = request.env["l10n.ro.account.anaf.sync"].browse(anaf_config_id)
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
        anaf_oauth_url = anaf_config.anaf_oauth_url
        client_id = anaf_config.client_id
        odoo_oauth_url = user.get_base_url() + "/l10n_ro_account_anaf_sync/anaf_oauth"
        redirect_url = "%s?response_type=code&client_id=%s&redirect_uri=%s" % (
            anaf_oauth_url,
            client_id,
            odoo_oauth_url,
        )
        anaf_request_from_redirect = request.redirect(
            redirect_url, code=302, local=False
        )

        # This is the default for Authorization Code grant.
        # A successful response is 302 Found which triggers a redirect to the redirect_uri.
        # The response parameters are embedded in the query component (the part after ?)
        # of the redirect_uri in the Location header.
        # For example:
        # HTTP/1.1 302 Found
        # Location: https://my-redirect-uri.callback?code=js89p2x1
        # where the authorization code is js89p21.

        return anaf_request_from_redirect

    @http.route(
        ["/l10n_ro_account_anaf_sync/anaf_oauth"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def get_anaf_oauth_code(self, **kw):
        "Returns a text with the result of anaf request from redirect"
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        now = datetime.now()
        ANAF_Configs = request.env["l10n.ro.account.anaf.sync"].sudo()
        anaf_config = ANAF_Configs.search(
            [
                ("client_id", "!=", ""),
                ("last_request_datetime", ">", now - timedelta(seconds=90)),
            ]
        )
        message = ""
        if len(anaf_config) > 1:
            message = _(
                "More than one ANAF config requested authentification in the last minutes."
                "Please request them in order, waiting for 2 minutes between requests."
            )
        elif not anaf_config:
            message = _("The response was done too late.\nResponse was: kw=%s" % kw)

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
            redirect_uri = user.get_base_url() + "/l10n_ro_account_anaf_sync/anaf_oauth"
            data = {
                "grant_type": "authorization_code",
                "client_id": "%s",
                "client_secret": "%s",
                "code": "%s",
                "access_key": "%s",
                "redirect_uri": "%s",
            } % (
                anaf_config.client_id,
                anaf_config.client_secret,
                code,
                code,
                redirect_uri,
            )
            response = requests.post(
                anaf_config.anaf_oauth_url + "/token",
                data=data,
                headers=headers,
            )
            response_json = response.json()

            message = _("The response was finished.\nResponse was: %s" % response_json)
            anaf_config.write(
                {
                    "code": code,
                    "client_token_valability": now + timedelta(days=89),
                    "access_token": response_json.get("access_token", ""),
                    "refresh_token": response_json.get("refresh_token", ""),
                }
            )
        else:
            message = _("No code was found in the response.\nResponse was: %s" % kw)

        anaf_config.message_post(body=message)
        values = {"message": message}
        return str(values)
