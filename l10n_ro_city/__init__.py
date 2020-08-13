#
# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from . import models
from odoo import tools
import os


def post_init_hook(cr, registry):

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    file_city = "res.city.csv"
    with tools.file_open(path + "/" + file_city, mode="rb") as fp:
        tools.convert_csv_import(
            cr, "base", file_city, fp.read(), {}, mode="init", noupdate=True,
        )
