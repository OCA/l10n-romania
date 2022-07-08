# Copyright (C) 2022extERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = ["mail.thread", "res.company"]
    _name = "res.company"

    anaf_callback_url = fields.Char(
        compute="_compute_anaf_callback_url",
        help="This is the address to set in anaf_portal_url "
        "( and will work if is https & accessible form internet)",
    )
    l10n_ro_edi_client_id = fields.Char(
        string="Client ID",
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
        default="",
    )
    l10n_ro_edi_client_secret = fields.Char(
        string="Client Secret",
        help="From ANAF site the Oauth id - view the readme",
        tracking=1,
        default="",
    )
    l10n_ro_edi_code = fields.Char(
        string="Code",
        help="Received from ANAF with this you can take access token and refresh_token",
        tracking=1,
        default="",
    )

    l10n_ro_edi_access_token = fields.Char(
        string="Access Token", help="Received from ANAF", tracking=1, default=""
    )
    l10n_ro_edi_refresh_token = fields.Char(
        string="Refresh Token", help="Received from ANAF", tracking=1, default=""
    )

    client_token_valability = fields.Date(
        help="Date when is going to expire - 90 days from when was generated",
        readonly=1,
        tracking=1,
    )

    response_secret = fields.Char(
        help="A generated secret to know that the response is ok", readonly=1
    )
    anaf_request_datetime = fields.Datetime(
        help="Time when was last time pressed the Get Token From Anaf Website."
        " It waits for ANAF request for maximum 1 minute",
        readonly=1,
    )
    other_responses = fields.Text(
        help="This are request to the page /anaf_oauth that are not finished"
        " with a received token. Date is in UTC",
        default="",
    )

    def _compute_anaf_callback_url(self):
        url = self.get_base_url()
        self.write({"anaf_callback_url": url + "/anaf_oauth"})

    def get_token_from_anaf_website(self):
        self.ensure_one()
        if self.l10n_ro_edi_access_token:
            resp = f"UTC{str(fields.datetime.now())[:19]} First revoke existing Access Token"
            to_write = {"other_responses": resp + self.other_responses}
            self.write(to_write)
            return
        return {
            "type": "ir.actions.act_url",
            "url": f"/redirect_anaf/{self.id}",
            "target": "new",
        }

    def test_anaf_api(self):
        self.ensure_one()
        url = "https://api.anaf.ro/TestOauth/jaxrs/hello?name=test_from_odoo"

        response = requests.get(
            url,
            data={"name": "rr"},
            headers={
                # 'Content-Type': 'application/json',
                "Content-Type": "multipart/form-data",
                "Authorization": f"Bearer {self.l10n_ro_edi_access_token}",
            },
            timeout=80,
        )
        anaf_hello_test = (
            f"UTC{str(fields.datetime.now())[:19]}{response.url=}\n"
            f"{response.reason=}\n{response.content=}\n"
            f"{response.status_code=}\n{response.headers=}\n"
            f"{response.request.headers=}\n{response.request.method=}\n"
        )

        #        _logger.info(anaf_hello_test)
        self.write(
            {"other_responses": "%s %s" % (anaf_hello_test, self.other_responses)}
        )
        return

    def revoke_access_token(self):
        self.ensure_one()
        resp = f"UTC{str(fields.datetime.now())[:19]}"
        if not self.l10n_ro_edi_access_token:
            self.write(
                {
                    "other_responses": resp
                    + "Can not revoke acces token - you do not have one"
                    + self.other_responses
                }
            )
            return
        param = {
            "client_id": f"{self.l10n_ro_edi_client_id}",
            "client_secret": f"{self.l10n_ro_edi_client_secret}",
            "access_token": f"{self.l10n_ro_edi_access_token}",
            #            "refresh_token": should function for refresh function
            "token_type_hint": "access_token",  # refresh_token  (should work without)
        }
        url = "https://logincert.anaf.ro/anaf-oauth2/v1/revoke"
        response = requests.post(
            url,
            data=param,
            timeout=80,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp += (
            f"REVOKE TOKEN{response.url=}\n{response.reason=}\n"
            f"{response.content=}\n{response.status_code=}\n"
            f"{response.headers=}\n{response.request.headers=}\n"
            f"{response.request.method=}\n"
        )
        to_write = {"other_responses": resp + self.other_responses}
        if response.reason == "OK":
            to_write.update(
                {
                    "code": "",
                    "l10n_ro_edi_access_token": "",
                    "l10n_ro_edi_refresh_token": "",
                    "anaf_request_datetime": False,
                    "client_token_valability": False,
                }
            )
        self.write(to_write)
        return
