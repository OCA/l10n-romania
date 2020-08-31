# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import models

from odoo import tools
import os


def post_init_hook(cr, registry):

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    files = ["res.country.zone.csv", "res.country.state.csv", "res.country.commune.csv"]
    for file in files:
        with tools.file_open(path + "/" + file, mode="rb") as fp:
            tools.convert_csv_import(
                cr, "base", file, fp.read(), {}, mode="init", noupdate=True,
            )

    cr.execute(
        """
    UPDATE res_city
                SET commune_id = commune.id
            FROM
                res_country_commune as commune
            WHERE res_city.municipality = commune.name
    """
    )
