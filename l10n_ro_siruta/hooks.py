# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os

from odoo import SUPERUSER_ID, api, tools


def post_init_hook(cr, registry):

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    files = ["res.country.zone.csv", "res.country.state.csv", "res.country.commune.csv"]
    for file in files:
        with tools.file_open(path + "/" + file, mode="rb") as fp:
            tools.convert_csv_import(
                cr,
                "base",
                file,
                fp.read(),
                {},
                mode="init",
                noupdate=True,
            )
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env["res.partner"]._install_l10n_ro_siruta()
