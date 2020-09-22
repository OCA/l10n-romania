# ©  2008-20209 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


import time
from functools import reduce

from odoo import api, models


class ReportPickingDelivery(models.AbstractModel):
    _name = "report.abstract_report.delivery_report"
    _description = "ReportPickingDelivery"
    _template = None

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        return {
            "doc_ids": docids,
            "doc_model": report.model,
            "data": data,
            "time": time,
            "docs": self.env[report.model].browse(docids),
            "get_line": self._get_line,
            "get_totals": self._get_totals,
            "reduce": reduce,
        }

    def _get_line(self, move_line):
        res = {"price": 0.0, "amount": 0.0, "tax": 0.0, "amount_tax": 0.0}
        if move_line.sale_line_id:
            line = move_line.sale_line_id

            taxes_ids = (
                line.tax_id
            )  # line.product_id.taxes_id.filtered(lambda r: r.company_id == self.env.user.company_id)

            incl_tax = taxes_ids.filtered(lambda tax: tax.price_include)

            if line.product_uom_qty != 0:
                res["price"] = line.price_subtotal / line.product_uom_qty
                if incl_tax:
                    list_price = line.price_total / line.product_uom_qty
                else:
                    list_price = res["price"]
            else:
                res["price"] = 0.0
                list_price = 0.0

            taxes_sale = taxes_ids.compute_all(list_price, quantity=move_line.product_qty, product=line.product_id)

            res["tax"] = taxes_sale["total_included"] - taxes_sale["total_excluded"]
            res["amount"] = taxes_sale["total_excluded"]
            res["amount_tax"] = taxes_sale["total_included"]

        return res

    def _get_totals(self, move_lines):
        res = {"amount": 0.0, "tax": 0.0, "amount_tax": 0.0}
        for move in move_lines:
            line = self._get_line(move)
            res["amount"] += line["amount"]
            res["tax"] += line["tax"]
            res["amount_tax"] += line["amount_tax"]
        return res


class ReportPickingReception(models.AbstractModel):
    _name = "report.abstract_report.reception_report"
    _description = "ReportPickingReception"
    _template = None

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        return {
            "doc_ids": docids,
            "doc_model": report.model,
            "data": data,
            "time": time,
            "docs": self.env[report.model].browse(docids),
            "get_line": self._get_line,
            "get_totals": self._get_totals,
            "reduce": reduce,
        }

    def _get_line(self, move):
        res = {"price": 0.0, "amount": 0.0, "tax": 0.0, "amount_tax": 0.0, "amount_sale": 0.0, "margin": 0.0}

        currency = move.company_id.currency_id

        if move.purchase_line_id:
            # todo: ce fac cu receptii facute cu preturi diferite ????
            line = move.purchase_line_id

            # todo:
            #  de verificat daca pretul din miscare este actualizat inainte de
            #  confirmarea transferului pentru a se actualiza cursul valutar !!
            res["price"] = move.price_unit  # pretul caculat la genereare miscarii

            value = 0
            quantity = 0
            for valuation in move.stock_valuation_layer_ids:
                value += valuation.value
                quantity += valuation.quantity
            if move.stock_valuation_layer_ids:
                res["price"] = value / (quantity or 1)

            # la loturi nu este completat move_line.price_unit
            # if move_line.price_unit == 0:
            #     if move_line.remaining_qty != 0:
            #         res['price'] = move_line.remaining_value /  move_line.remaining_qty

            taxes = line.taxes_id.compute_all(
                res["price"], quantity=move.product_qty, product=move.product_id, partner=move.partner_id
            )

            res["tax"] = taxes["total_included"] - taxes["total_excluded"]
            res["amount"] = taxes["total_excluded"]
            res["amount_tax"] = taxes["total_included"]

            taxes_ids = line.product_id.taxes_id.filtered(lambda r: r.company_id == move.company_id)
            list_price = move.product_id.list_price
            # incl_tax = taxes_ids.filtered(lambda tax: tax.price_include)
            # if incl_tax:
            #     list_price = incl_tax.compute_all(move_line.product_id.list_price)['total_excluded']
            # else:
            #     list_price = move_line.product_id.list_price

            taxes_sale = taxes_ids.compute_all(
                list_price, currency=currency, quantity=move.product_uom_qty, product=move.product_id
            )

            res["amount_sale"] = taxes_sale["total_excluded"]
            res["tax_sale"] = taxes_sale["total_included"] - taxes_sale["total_excluded"]
            res["amount_tax_sale"] = taxes_sale["total_included"]
            #  conversie pret din pretul din unitatea de masura de baza in pret in unitatea de masura din document
            res["price"] = res["price"] * line.product_uom._compute_quantity(1, line.product_id.uom_id)
            if res["amount_tax"] != 0.0:
                res["margin"] = 100 * (taxes_sale["total_included"] - res["amount_tax"]) / res["amount_tax"]
            else:
                res["margin"] = 0.0
        else:
            # receptie fara comanda de aprovizionare

            value = move.value
            res["price"] = abs(move.price_unit)

            # res['amount'] = currency.round(value)
            # if move_line.product_uom_qty != 0:
            #     res['price'] = currency.round(value) / move_line.product_uom_qty
            # else:
            #     res['price'] = 0.0

            taxes_ids = move.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == move.company_id)
            taxes = taxes_ids.compute_all(
                res["price"],
                currency=currency,
                quantity=move.product_uom_qty,
                product=move.product_id,
                partner=move.partner_id,
            )
            res["amount"] = taxes["total_excluded"]
            res["tax"] = taxes["total_included"] - taxes["total_excluded"]
            res["amount_tax"] = taxes["total_included"]

            taxes_ids = move.product_id.taxes_id.filtered(lambda r: r.company_id == move.company_id)
            incl_tax = taxes_ids.filtered(lambda tax: tax.price_include)
            # if incl_tax:
            #     list_price = incl_tax.compute_all(move_line.product_id.list_price)['total_excluded']
            # else:

            list_price = move.product_id.list_price

            taxes_sale = taxes_ids.compute_all(
                list_price, currency=currency, quantity=move.product_uom_qty, product=move.product_id
            )

            res["amount_sale"] = taxes_sale["total_excluded"]
            res["tax_sale"] = taxes_sale["total_included"] - taxes_sale["total_excluded"]
            res["amount_tax_sale"] = taxes_sale["total_included"]

            if taxes["total_included"] != 0.0:
                res["margin"] = 100 * (taxes_sale["total_included"] - taxes["total_included"]) / taxes["total_included"]
            else:
                res["margin"] = 0.0

        return res

    def _get_totals(self, move_lines):
        res = {
            "amount": 0.0,
            "tax": 0.0,
            "amount_tax": 0.0,
            "amount_sale": 0.0,
            "tax_sale": 0.0,
            "amount_tax_sale": 0.0,
        }
        for move in move_lines:
            line = self._get_line(move)
            res["amount"] += line["amount"]
            res["tax"] += line["tax"]
            res["amount_tax"] += line["amount_tax"]

            res["amount_sale"] += line["amount_sale"]
            res["tax_sale"] += line["tax_sale"]
            res["amount_tax_sale"] += line["amount_tax_sale"]
        return res


class ReportDelivery(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_delivery"
    _description = "Report delivery"
    _inherit = "report.abstract_report.delivery_report"
    _template = "l10n_ro_stock_picking_report.report_delivery"
    # _wrapped_report_class = picking_delivery


class ReportDeliveryPrice(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_delivery_price"
    _description = "Report delivery in store"
    _inherit = "report.abstract_report.delivery_report"
    _template = "l10n_ro_stock_picking_report.report_delivery_price"
    # _wrapped_report_class = picking_delivery


class ReportConsumeVoucher(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_consume_voucher"
    _description = "Report consume voucher"
    _inherit = "report.abstract_report.delivery_report"
    _template = "l10n_ro_stock_picking_report.report_consume_voucher"
    # _wrapped_report_class = picking_delivery


class ReportInternalTransfer(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_internal_transfer"
    _description = "Report transfer"
    _inherit = "report.abstract_report.delivery_report"
    _template = "l10n_ro_stock_picking_report.report_internal_transfer"
    # _wrapped_report_class = picking_delivery


class ReportReception(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_reception"
    _description = "Report reception"
    _inherit = "report.abstract_report.reception_report"
    _template = "l10n_ro_stock_picking_report.report_reception"
    # _wrapped_report_class = picking_reception


class ReportReceptionNoTax(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_reception_no_tax"
    _description = "Report reception no tax"
    _inherit = "report.abstract_report.reception_report"
    _template = "l10n_ro_stock_picking_report.report_reception_no_tax"
    # _wrapped_report_class = picking_reception


class ReportReceptionSalePrice(models.AbstractModel):
    _name = "report.l10n_ro_stock_picking_report.report_reception_sale_price"
    _description = "Report reception in store"
    _inherit = "report.abstract_report.reception_report"
    _template = "l10n_ro_stock_picking_report.report_reception_sale_price"
    # _wrapped_report_class = picking_reception
