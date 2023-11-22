# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
from datetime import date, datetime
from subprocess import PIPE, Popen

from odoo import api, fields, models, tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends("l10n_ro_vat_number")
    def _compute_l10n_ro_anaf_history(self):
        for partner in self:
            if partner.l10n_ro_vat_number:
                history = self.env["l10n.ro.res.partner.anaf"].search(
                    [("vat", "=", partner.l10n_ro_vat_number)]
                )
                partner.l10n_ro_anaf_history = [(6, 0, [line.id for line in history])]
            else:
                partner.l10n_ro_anaf_history = [(6, 0, [])]

    l10n_ro_vat_on_payment = fields.Boolean(string="Romania - VAT on Payment")
    l10n_ro_anaf_history = fields.One2many(
        "l10n.ro.res.partner.anaf",
        compute="_compute_l10n_ro_anaf_history",
        string="Romania - ANAF History",
        readonly=True,
    )

    @api.model
    def _insert_relevant_anaf_data(self):
        """Load VAT on payment lines for specified partners."""

        def format_date(strdate):
            if strdate != "":
                return datetime.strptime(str(strdate), "%Y%m%d").strftime(DATE_FORMAT)

        vat_numbers = [
            p.l10n_ro_vat_number
            for p in self
            if p.vat and p.vat.lower().startswith("ro") and p.vat[2:].isnumeric()
        ]
        if vat_numbers == []:
            return
        anaf_obj = self.env["l10n.ro.res.partner.anaf"]
        data_dir = tools.config["data_dir"]
        istoric = os.path.join(data_dir, "istoric.txt")
        vat_regex = "^[0-9]+#(%s)#" % "|".join(vat_numbers)
        anaf_data = Popen(["egrep", vat_regex, istoric], stdout=PIPE)
        (process_lines, _) = anaf_data.communicate()
        process_lines = [x.split("#") for x in process_lines.decode().strip().split()]
        lines = self.env["l10n.ro.res.partner.anaf"].search(
            [("anaf_id", "in", [x[0] for x in process_lines])]
        )
        line_ids = [newline.anaf_id for newline in lines]
        for line in process_lines:
            if line[0] not in line_ids:
                anaf_obj.create(
                    {
                        "anaf_id": line[0],
                        "vat": line[1],
                        "start_date": format_date(line[2]),
                        "end_date": format_date(line[3]),
                        "publish_date": format_date(line[4]),
                        "operation_date": format_date(line[5]),
                        "operation_type": line[6],
                    }
                )

    def _check_vat_on_payment(self):
        self.ensure_one()
        ctx = dict(self._context)
        vat_on_payment = False
        self._insert_relevant_anaf_data()
        self._compute_l10n_ro_anaf_history()
        if self.l10n_ro_anaf_history:
            if ctx.get("check_date", False):
                line = self.env["l10n.ro.res.partner.anaf"].search(
                    [
                        ("id", "in", [rec.id for rec in self.l10n_ro_anaf_history]),
                        ("start_date", "<=", ctx["check_date"]),
                    ],
                    limit=1,
                )
            else:
                line = self.l10n_ro_anaf_history[0]
            if line:
                vat_on_payment = True
                if line.end_date and line.end_date <= ctx.get("check_date", False):
                    vat_on_payment = False
        elif self.l10n_ro_vat_on_payment:
            vat_on_payment = True
        return vat_on_payment

    def check_vat_on_payment(self):
        ctx = dict(self._context)
        ctx.update({"check_date": date.today()})

        for partner in self:
            partner.l10n_ro_vat_on_payment = partner.with_context(
                **ctx
            )._check_vat_on_payment()

    @api.model
    def update_vat_payment_all(self):
        self.env["l10n.ro.res.partner.anaf"]._download_anaf_data()
        partners = self.search([("vat", "!=", False), ("country_id.code", "=", "RO")])
        partners.check_vat_on_payment()

    @api.model
    def _update_vat_payment_all(self):
        self.update_vat_payment_all()

    @api.model_create_multi
    def create(self, vals_list):
        partner = super().create(vals_list)
        partner.filtered(
            lambda p: p.country_code == "RO" and p.vat
        ).check_vat_on_payment()
        return partner

    def write(self, vals):
        res = super().write(vals)
        if "vat" in vals:
            self.filtered(
                lambda partner: partner.country_code == "RO"
            ).check_vat_on_payment()
        return res
