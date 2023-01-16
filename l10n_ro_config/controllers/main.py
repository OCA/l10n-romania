# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.main import Home


class L10nRoHome(Home):
    @http.route()
    def web_load_menus(self, unique):
        ctx = {**request.context}
        ctx.update(menus_current_company="")
        if request.params.get("company"):
            comp_str = request.params["company"].split(",")[0]
            comp = int(comp_str)
            ctx.update(menus_current_company=comp)
        request.context = ctx
        return super().web_load_menus(unique)
