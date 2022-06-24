from odoo import http
from odoo.http import request
import secrets
from datetime import datetime, timedelta
import requests
# Authorization Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/authorize
# Token Issuance Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/token
# Token Revocation Endpoint https://logincert.anaf.ro/anaf-oauth2/v1/revoke


class WebsitePageDepositKpi(http.Controller):
    @http.route(
        ["/redirect_anaf/<int:company_id>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def redirect_anaf(self, company_id, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        if user.share:
            return "This page is only for internal users!"
        company = request.env["res.company"].browse(company_id)
        if not company.exists():
            return "Error, this company does not exist!"
        elif not company.client_id or not company.client_secret:
            return f"Error, on company {company.name} you does not have a Oauth client_id or client_secret for anaf.ro!"

        secret = secrets.token_urlsafe(16)
        company.write(
            {
                "response_secret": secret,
                "anaf_request_datetime": datetime.now(),
            }
        )
        anafOauth = (
            "https://logincert.anaf.ro/anaf-oauth2/v1/authorize"
            f"?client_id={company.client_id}"
            f"&client_secret={company.client_secret}"
            "&response_type=code"
            f"&redirect_uri={user.get_base_url()+'/anaf_oauth'}"
            f"&scope={secret}"  # is not giving it back in Oauth they should
       #     "&grant_type=authorization_code"  # not necessary?
        )
# alex: here should be POST and not get, but is another redirect
#        response = request.redirect(anafOauth, code=302, local=False)
        try:
            response = requests.post(f"{user.get_base_url()}/redirect_anaf_post", 
                    json={
                "client_id":f"{company.client_id}",
                "client_secret":f"{company.client_secret}",
                "response_type":"code",
                "redirect_uri":f"{user.get_base_url()+'/anaf_oauth'}",
                "scope":f"{secret}"  # is not giving it back in Oauth they should
                    }, 
                    #headers = {"Content-type": "application/x-www-form-urlencoded"},
                    headers={'Content-Type': 'multipart/form-data'},
                    timeout = 30,
                    )
            response.raise_for_status()
        except Exception as ex:
            return f"Something went wrong during post  ex={ex}"
            

        return response

    @http.route(
        ["/redirect_anaf_post"],
        type="http",
        auth="public",
        csrf=False,
        website=True,
        sitemap=False,
    )
    def redirect_anaf_post(self,  **kw):
        response = request.redirect("https://logincert.anaf.ro/anaf-oauth2/v1/authorize", code=302, local=False)
        return response
        
        
        
    @http.route(
        ["/anaf_oauth"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def get_anaf_oauth_code(self, **kw):
        uid = request.uid
        user = request.env["res.users"].browse(uid)
        now = datetime.now()
        Companies = request.env["res.company"].sudo()
        company = Companies.search(
            [("client_id", "!=", ""), ('anaf_request_datetime',">",now-timedelta(minutes=1))])
        error = ""
        if len(company) > 1:
            ret = f"UTC{str(now)[:19]} found {company} that have done request to anaf. We can not set to more than one at a time. Rreponse was {kw}\n"
            for comp in company:
                resp = ret + (comp.other_responses or "")
                comp.write({"other_responses": resp})
            return ret
        elif not company:
            return f"You can not modify anything, the reponse is to late.\nkw={kw}"
        code = kw.get("code")
        if code:
            ret= f"UTC{str(now)[:19]} All is OK reponse kw={kw}\n"
            company.write(
                {
                    "client_received_token": code,
                    "client_token_valability": now + timedelta(days=89),
                    "other_responses": ret,
                }
            )
            return ret
        else:
            error = f"UTC{str(now)[:19]} BAD reponse no code in reponse kw={kw}\n"
            company.write({"other_responses": error})
            return f"UTC{str(now)[:19]} BAD reponse no 'code' in reponse kw={kw}\n"
