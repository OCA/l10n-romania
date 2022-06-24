# Copyright (C) 2022extERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = ["mail.thread", "res.company"]
    _name = "res.company"

    anaf_callback_url = fields.Char(
        compute="_compute_anaf_callback_url",
        help="This is the address to set in anaf_portal_url ( and will work if is https & accesible form internet)",
    )
    client_id = fields.Char(
        help="From anaf site the Oauth id - view the readme", tracking=1
    )
    client_secret = fields.Char(
        help="From anaf site the Oauth id - view the readme", tracking=1
    )
    client_received_token = fields.Char(
        help="Recived from ANAF if called with right data and usb signature", tracking=1
    )
    client_token_valability = fields.Date(
        help="date when is going to exprire - 90 days from when was generated",
        readonly=1,
        tracking=1,
    )
    client_token_response = fields.Char(
        help="date when is going to exprire - 90 days from when was generated",
        readonly=1,
        tracking=1,
    )
    response_secret = fields.Char(
        help="A generated secret to know that the response is ok", readonly=1
    )
    response_secret_duration = fields.Datetime(
        help="Time till when will wait for a reponse from anaf with the secret (1 minute after request)",
        readonly=1,
    )
    other_responses = fields.Text(
        help="This are request to the page /anaf_oauth that are not finished with a received token. Date is in UTC"
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
