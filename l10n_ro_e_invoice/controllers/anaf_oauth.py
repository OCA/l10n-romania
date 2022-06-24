from odoo import http
from odoo.http import request
import secrets
from datetime import datetime, timedelta

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
        company.write({'response_secret':secret, "response_secret_duration":datetime.now()+timedelta(minutes=1)})
        anafOauth = ("https://logincert.anaf.ro/anaf-oauth2/v1/authorize"
                f"?client_id={company.client_id}" 
                f"&client_secret={company.client_secret}" 
                "&response_type=code" 
                f"&redirect_uri={user.get_base_url()+'/anaf_oauth'}"
                '&grant_type=authorization_code'  # not necessary?
                f"&scope={secret}"   # is not giving it back in Oauth they should
                )
        response = request.redirect(anafOauth, code=302, local=False)   
        return response
    
#The following example shows an HTTP request that is sent to the revocation endpoint:
#POST /revoke HTTP/1.1
#Host: server.example.com
#Content-Type: application/x-www-form-urlencoded
#Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
#token=45ghiukldjahdnhzdauz&token_type_hint=access_token    
    
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
        company = Companies.search([("client_id","!=","")])#, ('response_secret_duration',">",now)])
        error = ""
        if len(company) > 1:
            ret = f"UTC{str(now)[:19]} found {company} that have done request to anaf. We can not set to more than one at a time. Rreponse was {kw}\n"
            for comp in company:
                resp = ret + (comp.other_responses or "")
                comp.write({"other_responses": resp})
            return  ret
        elif not company:
            return f"You can not modify anything, the reponse is to late.\nkw={kw}"
        code = kw.get("code")
        if code:  
            company.write({"client_token_response": code,
                           "client_token_valability": now+timedelta(days=89),
                           "other_responses": f"UTC{str(now)[:19]} OK reponse kw={kw}\n"
                           })
            return f"put code form kw={kw} in {company}"
        else:
            error = f"UTC{str(now)[:19]} BAD reponse no code in reponse kw={kw}\n"
            company.write({"other_responses": error })
            return f"UTC{str(now)[:19]} BAD reponse no 'code' in reponse kw={kw}\n"
