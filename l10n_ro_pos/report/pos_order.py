# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from datetime import timedelta

import pytz

from odoo import api, fields, models


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs,
    ):
        res = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )

        # Acelasi domeniu de comenzi ca raportul standard, ca sa calculam costul marfii.
        # Conditii in AND implicit (liste concatenate); evitam osv.expression.AND,
        # deprecat din 19.0 in favoarea odoo.fields.Domain.
        domain = [("state", "in", ["paid", "invoiced", "done"])]

        if session_ids:
            domain += [("session_id", "in", session_ids)]
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # implicit: azi 00:00:00 in fusul orar al utilizatorului
                user_tz = pytz.timezone(
                    self.env.context.get("tz") or self.env.user.tz or "UTC"
                )
                today = user_tz.localize(
                    fields.Datetime.from_string(fields.Date.context_today(self))
                )
                date_start = today.astimezone(pytz.timezone("UTC"))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # evitam un date_stop mai mic decat date_start
                if date_stop < date_start:
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # implicit: azi 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain += [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
            ]

            if config_ids:
                domain += [("config_id", "in", config_ids)]

        # Valoarea de stoc are sens doar cu valorizarea (stock_account) instalata;
        # campul `value` pe stock.move vine de acolo. Daca lipseste, raportul ramane
        # functional (coloanele afiseaza 0).
        if "value" not in self.env["stock.move"]._fields:
            res["total_stock_amount"] = 0.0
            return res

        orders = self.env["pos.order"].search(domain)

        # In O19 SVL a fost eliminat; valorizarea e pe stock.move (value / quantity).
        # Miscari valorizate = is_in/is_out (transferul intern nu e valorizat nativ).
        # Acumulam valoare/cantitate per produs pentru un cost mediu unitar.
        products_stock = {}
        products_stock_qty = {}

        for order in orders:
            for picking in order.picking_ids:
                for move in picking.move_ids:
                    if not (move.is_in or move.is_out):
                        continue
                    products_stock.setdefault(move.product_id.id, 0.0)
                    products_stock_qty.setdefault(move.product_id.id, 0.0)
                    products_stock[move.product_id.id] += abs(move.value)
                    products_stock_qty[move.product_id.id] += abs(move.quantity)

        def _stock_price(product_id):
            if product_id in products_stock and products_stock_qty.get(product_id):
                return products_stock[product_id] / products_stock_qty[product_id]
            return 0.0

        # In Odoo 19 res["products"] / res["refund_products"] sunt liste de categorii,
        # fiecare cu lista ei de produse. Injectam costul pe fiecare linie.
        total_stock_amount = 0.0
        for category in res.get("products", []):
            for line in category.get("products", []):
                stock_price = _stock_price(line.get("product_id"))
                line["stock_price"] = stock_price
                line["stock_amount"] = stock_price * line.get("quantity", 0.0)
                total_stock_amount += line["stock_amount"]

        for category in res.get("refund_products", []):
            for line in category.get("products", []):
                stock_price = _stock_price(line.get("product_id"))
                line["stock_price"] = stock_price
                line["stock_amount"] = stock_price * line.get("quantity", 0.0)

        res["total_stock_amount"] = total_stock_amount
        return res
