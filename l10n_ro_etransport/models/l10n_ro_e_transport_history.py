# Copyright (C) 2024 Deltatech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ETransportHistory(models.Model):
    _name = "l10n.ro.e.transport.history"
    _description = "E Transport History"

    # uit	string
    # cod_decl	string
    # ref_decl	string
    # sursa	string
    # id_incarcare	string
    # data_creare	string
    # tip_op	string
    # data_transp	string
    # pc_tara	string
    # pc_cod	string
    # pc_den	string
    # tr_tara	string
    # tr_cod	string
    # tr_den	string
    # nr_veh	string
    # nr_rem1	string
    # nr_rem2	string

    name = fields.Char("UIT")
    cod_decl = fields.Char()
    ref_decl = fields.Char("Reference")
    sursa = fields.Char()
    id_incarcare = fields.Char()

    date = fields.Datetime("Data Creare")
    vehicle = fields.Char()
    trailer1 = fields.Char()
    trailer2 = fields.Char()

    transport_date = fields.Date()
    pc_den = fields.Char()
    tr_den = fields.Char("Carrier Name")
    errors = fields.Text()
    operation_type_id = fields.Many2one("l10n.ro.e.transport.operation")
    country_tr_id = fields.Many2one("res.country", string="Country TR")
    country_pc_id = fields.Many2one("res.country", string="Country PC")

    @api.model
    def action_refresh(self):
        anaf_config = self.env.company._l10n_ro_get_anaf_sync(scope="e-transport")
        params = {}
        cif = self.env.company.partner_id.vat.replace("RO", "")
        func = f"/lista/60/{cif}"
        content, status_code = anaf_config._l10n_ro_etransport_call(
            func, params, method="GET"
        )
        if status_code != 200:
            raise UserError(
                _("Error %(status_code)s:%(content)s")
                % {"status_code": status_code, "content": content}
            )

        messages = content.get("mesaje", [])
        romania_tz = pytz.timezone("Europe/Bucharest")
        for message in messages:
            # data este de forma 20240620000000"

            date = datetime.strptime(message.get("data_creare"), "%Y%m%d%H%M%S")
            localized_date = romania_tz.localize(date)
            # Convertim data și ora la GMT
            gmt_tz = pytz.timezone("GMT")
            gmt_date = localized_date.astimezone(gmt_tz)
            message["data_creare"] = gmt_date.strftime("%Y-%m-%d %H:%M:%S")

            data = message.get("data_transp")
            data = data[:4] + "-" + data[4:6] + "-" + data[6:8]
            message["data_transp"] = data

            values = {
                "name": message.get("uit"),
                "date": message.get("data_creare"),
                "cod_decl": message.get("cod_decl"),
                "ref_decl": message.get("ref_decl"),
                "sursa": message.get("sursa"),
                "id_incarcare": message.get("id_incarcare"),
                "vehicle": message.get("nr_veh"),
                "trailer1": message.get("nr_rem1"),
                "trailer2": message.get("nr_rem2"),
                "transport_date": message.get("data_transp"),
                "pc_den": message.get("pc_den"),
                "tr_den": message.get("tr_den"),
            }
            errors = ""
            for mesaj in message.get("mesaje", []):
                errors += mesaj.get("tip", "") + ":" + mesaj.get("mesaj", "") + "\n"

            if errors:
                values["errors"] = errors

            tip_op = message.get("tip_op")
            if tip_op:
                operation_type = self.env["l10n.ro.e.transport.operation"].search(
                    [("code", "=", tip_op)], limit=1
                )
                if operation_type:
                    values["operation_type_id"] = operation_type.id

            tr_tara = message.get("tr_tara")
            if tr_tara:
                country = self.env["res.country"].search(
                    [("code", "=", tr_tara)], limit=1
                )
                if country:
                    values["country_tr_id"] = country.id
            pc_tara = message.get("pc_tara")
            if pc_tara:
                country = self.env["res.country"].search(
                    [("code", "=", pc_tara)], limit=1
                )
                if country:
                    values["country_pc_id"] = country.id

            uit = message.get("uit")
            domain = [("name", "=", uit)]
            th = self.search(domain, limit=1)
            if th:
                th.write(values)
            else:
                self.create(values)
