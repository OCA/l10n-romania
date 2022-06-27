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
    client_id = fields.Char(
        help="From ANAF site the Oauth id - view the readme", tracking=1
    )
    client_secret = fields.Char(
        help="From ANAF site the Oauth id - view the readme", tracking=1
    )
    code = fields.Char(
        help="Received from ANAF with this you can take access token and refresh_token",
        tracking=1,
    )

    access_token = fields.Char(help="Received from ANAF", tracking=1, readonly=1)
    refresh_token = fields.Char(help="Received from ANAF", tracking=1, readonly=1)

    client_token_valability = fields.Date(
        help="Date when is going to expire - 90 days from when was generated",
        readonly=1,
        tracking=1
    )

    response_secret = fields.Char(
        help="A generated secret to know that the response is ok", readonly=1
    )
    anaf_request_datetime = fields.Datetime(
        help="Time when was last time pressed the Get Token From Anaf Website."
        " It waits for ANAF request for maximum 1 minute",
        readonly=1
    )
    other_responses = fields.Text(
        help="This are request to the page /anaf_oauth that are not finished"
        " with a received token. Date is in UTC"
    )

    def _compute_anaf_callback_url(self):
        url = self.get_base_url()
        self.write({"anaf_callback_url": url + "/anaf_oauth"})

    def get_token_from_anaf_website(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/redirect_anaf/{self.id}",
            "target": "new",
        }

    def test_anaf_api(self):
        self.ensure_one()
        # param = {
        #     # "client_id":f"{self.client_id}",
        #     # "token":f"{self.client_received_token}",
        #     # "code":f"{self.client_received_token}",
        #     # "key":f"{self.client_received_token}",
        #     # "access_token":f"{self.client_received_token}",
        #     # "name":"xx",
        # }
        # it should work, but is giving 403 Forbidden
        url = "https://api.anaf.ro/TestOauth/jaxrs/hello?name=yy"
        #  url = "https://api.anaf.ro/test/FCTEL/rest/listaMesajeFactura"
        #  url = "https://api.anaf.ro/test/FCTEL/rest/descarcare"
        #       id = index descarare factura
        #  url = "https://api.anaf.ro/test/ETRANSPORT/ws/v1/lista/{1}/{}"

        response = requests.get(
            url,
            #        response = requests.post(url,
            #                                data={"id":1},
            # json=json.dumps(param),
            headers={  # 'Content-Type': 'application/json',
                "Content-Type": "multipart/form-data",
                # 'Accept': 'application/json',
                # "client_id": self.client_id,
                "Authorization": f"Bearer {self.access_token}",
            },
            timeout=80,
            #                allow_redirects=True
        )
        # return f"{response.content=}\n{response.headers=}"
        anaf_hello_test = (
            f"UTC{str(fields.datetime.now())[:19]}{response.url=}\n"
            f"{response.reason=}\n{response.content=}\n"
            f"{response.status_code=}\n{response.headers=}\n"
            f"{response.request.headers=}\n{response.request.method=}\n"
        )

        _logger.info(anaf_hello_test)
        self.write({"other_responses": anaf_hello_test + self.other_responses})
        return
        # for a popup in future, or put in a text field?
        # return {
        #     "name": "My Window",
        #     "domain": [],
        #     "res_model": "my.model",
        #     "type": "ir.actions.act_window",
        #     "view_mode": "form",
        #     "view_type": "form",
        #     "context": {},
        #     "target": "new",
        # }
