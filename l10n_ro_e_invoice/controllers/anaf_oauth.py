import secrets
from datetime import datetime, timedelta

import requests

from odoo import _, http
from odoo.http import request

# Authorization Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/authorize
# Token Issuance Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/token
# Token Revocation Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/revoke


class WebsitePageDepositKpi(http.Controller):
    @http.route(
        ["/redirect_anaf/<int:company_id>"],
        type="http",
        auth="user",
        website=False,
        sitemap=False,
    )
    def redirect_anaf(self, company_id, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        error = False
        if user.share:
            return request.not_found(_("This page is only for internal users!"))

        company = request.env["res.company"].browse(company_id)
        if not company.exists():
            return request.not_found(_("Error, this company does not exist!"))

        elif not company.client_id or not company.client_secret:
            error = (
                f"Error, on company {company.name} you does not have a "
                f"Oauth client_id or client_secret for anaf.ro!"
            )

        secret = secrets.token_urlsafe(16)
        now = datetime.now()
        if (
            company.anaf_request_datetime
            and company.anaf_request_datetime + timedelta(seconds=30) > now
        ):
            error = _("You can make only one request per minute")

        if error:
            values = {"error": error}
            return request.render("l10n_ro_e_invoice.redirect_anaf", values)

        company.write(
            {
                "response_secret": secret,
                "anaf_request_datetime": now,
            }
        )
        anafOauth = (
            "https://logincert.anaf.ro/anaf-oauth2/v1/authorize?"
            "response_type=code"
            f"&client_id={company.client_id}"
            f"&redirect_uri={user.get_base_url() + '/anaf_oauth'}"
           # f"&scope={secret}"
        )
        anaf_request_from_redirect = request.redirect(anafOauth, code=302, local=False)
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
        ["/anaf_oauth"], type="http", auth="public", website=False, sitemap=False
    )
    def get_anaf_oauth_code(self, **kw):
        "Returns a text with the result of anaf request from redirect"
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        now = datetime.now()
        Companies = request.env["res.company"].sudo()
        company = Companies.search(
            [
                ("client_id", "!=", ""),
                ('anaf_request_datetime',">",now-timedelta(minutes=1))
            ],
            limit=1,
        )
        message = ""
        if len(company) > 1:
            message = (
                f"UTC{str(now)[:19]} found {company} that have done request to anaf."
                f" We can not set to more than one at a time. response was {kw}\n"
            )
            for comp in company:
                resp = message
                comp.write({"other_responses": resp + (company.other_responses or "")})

        elif not company:
            message = (
                f"You can not modify anything, the response is to late.\n"
                f" Response was: kw={kw}"
            )

        if message:
            values = {"message": message}
            return request.render("l10n_ro_e_invoice.redirect_anaf", values)

        code = kw.get("code")
        if code:
            message = f"UTC{str(now)[:19]} All is OK response kw={kw}\n"

            headers = {"content-type": "application/x-www-form-urlencoded",
                       "accept":"application/json",
                       "user-agent":"PostmanRuntime/7.29.2",
                       }
            data = {
                "grant_type": "authorization_code",
                "client_id": f"{company.client_id}",
                "client_secret": f"{company.client_secret}",
                "code": f"{code}",
                "access_key":  f"{code}",
                "redirect_uri": f"{user.get_base_url() + '/anaf_oauth'}",
            }
            response = requests.post(
                "https://logincert.anaf.ro/anaf-oauth2/v1/token",
                data=data,
                headers=headers,
            )
            response_json = response.json()
            message += f" {response_json=}\n\n"
            company.write(
                {
                    "code": code,
                    "client_token_valability": now + timedelta(days=89),
                    "other_responses": message + (company.other_responses or ""),
                    "access_token": response_json.get("access_token", ""),
                    "refresh_token": response_json.get("refresh_token", ""),
                }
            )
            message = "All is OK response."
        else:
            error = f"UTC{str(now)[:19]} BAD response no code in response kw={kw}\n"
            company.write({"other_responses": error + (company.other_responses or "")})
            message = f"UTC{str(now)[:19]} BAD response no 'code' in response kw={kw}\n"

        values = {"message": message}
# does not have a user and language, and is a error does not matter
#        return request.render("l10n_ro_e_invoice.redirect_anaf", values)
        return str(values)
