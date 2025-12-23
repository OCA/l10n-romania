# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.fields import Domain


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self, date_start=False, date_stop=False, config_ids=False, session_ids=False
    ):
        res = super().get_sale_details(date_start, date_stop, config_ids, session_ids)

        domain = [("state", "in", ["paid", "invoiced", "done"])]

        if session_ids:
            domain = Domain.AND([domain, [("session_id", "in", session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(
                    self.env.context.get("tz") or self.env.user.tz or "UTC"
                )
                today = user_tz.localize(
                    fields.Datetime.from_string(fields.Date.context_today(self))
                )
                date_start = today.astimezone(pytz.timezone("UTC"))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if date_stop < date_start:
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = Domain.AND(
                [
                    domain,
                    [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ],
                ]
            )

            if config_ids:
                domain = Domain.AND([domain, [("config_id", "in", config_ids)]])

        orders = self.env["pos.order"].search(domain)

        products_stock = {}
        products_stock_qty = {}
        products_sold = {}

        for order in orders:
            for line in order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty
            for picking in order.picking_ids:
                for move in picking.move_ids:
                    value = 0
                    quantity = 0
                    for valuation in move.stock_valuation_layer_ids:
                        if (
                            valuation.l10n_ro_valued_type == "internal_transfer"
                            and not valuation.account_move_id
                        ):
                            continue
                        if (
                            valuation.l10n_ro_valued_type == "dropshipped"
                            and valuation.value < 0
                        ):
                            continue
                        value += abs(valuation.value)
                        quantity += abs(valuation.quantity)

                    products_stock.setdefault(move.product_id.id, 0.0)
                    products_stock_qty.setdefault(move.product_id.id, 0.0)
                    products_stock[move.product_id.id] += value
                    products_stock_qty[move.product_id.id] += quantity

        products = []
        total_stock_amount = 0
        for (product, price_unit, discount), qty in products_sold.items():
            values = {
                "product_id": product.id,
                "product_name": product.name,
                "code": product.default_code,
                "quantity": qty,
                "price_unit": price_unit,
                "discount": discount,
                "uom": product.uom_id.name,
            }
            stock_price = 0
            if product.id in products_stock:
                if products_stock_qty[product.id]:
                    stock_price = (
                        products_stock[product.id] / products_stock_qty[product.id]
                    )
            values["stock_price"] = stock_price
            values["stock_amount"] = stock_price * qty
            products += [values]
            total_stock_amount += stock_price * qty

        # res["products"] = sorted(products, key=lambda l: l["product_name"])
        res["total_stock_amount"] = total_stock_amount
        return res
