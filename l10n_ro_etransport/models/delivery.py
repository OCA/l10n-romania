# ©  2024 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    l10n_ro_e_partner_id = fields.Many2one("res.partner", string="Partner Carrier")
