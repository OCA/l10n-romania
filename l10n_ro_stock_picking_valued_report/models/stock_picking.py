# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    l10n_ro_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_l10n_ro_valued_fields",
        string="Currency",
        compute_sudo=True,  # See explanation for sudo in compute method,
    )
    l10n_ro_amount_untaxed = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Untaxed Amount",
        compute_sudo=True,  # See explanation for sudo in compute method,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_amount_tax = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Taxes",
        compute_sudo=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_amount_total = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Total",
        compute_sudo=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_is_internal = fields.Boolean(compute="_compute_l10n_ro_is_internal")
    l10n_ro_is_nir = fields.Boolean(
        compute="_compute_l10n_ro_is_nir",
        string="Is NIR",
        help="Romanian goods receipt note (Nota de intrare-receptie) - an "
        "incoming transfer registered by a Romanian company. Printed as a NIR "
        "instead of the standard delivery-style reception slip.",
    )

    @api.depends("picking_type_id.code", "company_id", "is_l10n_ro_record")
    def _compute_l10n_ro_is_nir(self):
        for pick in self:
            pick.l10n_ro_is_nir = bool(
                pick.is_l10n_ro_record
                and pick.company_id.country_id.code == "RO"
                and pick.picking_type_id.code == "incoming"
            )

    def _l10n_ro_nir_charge_breakdown(self):
        """Split the receipt's additional costs (landed costs) by type, for the
        breakdown printed under the NIR table.

        The amounts come from the landed-cost valuation adjustments booked on
        the receipt moves, grouped by the landed cost's own type
        (``l10n_ro_cost_type``: transport, excise, dvi, price difference...).
        The sum equals the ``Additional Charges`` column total, and the excise
        is taken only from a landed cost of type ``excise`` - never recomputed
        from the product excise category. Returns a list of
        ``(translated label, amount)`` in the selection's order, non-zero only."""
        self.ensure_one()
        landed_cost = self.env["stock.landed.cost"]
        labels = dict(
            landed_cost._fields["l10n_ro_cost_type"]._description_selection(self.env)
        )
        totals = {}
        adjustments = self.env["stock.valuation.adjustment.lines"].search(
            [("move_id", "in", self.move_ids.ids)]
        )
        for adj in adjustments:
            ctype = adj.cost_id.l10n_ro_cost_type or "normal"
            totals[ctype] = totals.get(ctype, 0.0) + adj.additional_landed_cost
        return [
            (labels.get(ctype, ctype), amount)
            for ctype, amount in totals.items()
            if amount
        ]

    def _l10n_ro_nir_report_lines(self):
        """Build the NIR table rows, one per receipt move, with the valued
        fields aggregated from the move lines and expressed in the product's
        reference UoM."""
        self.ensure_one()
        lines = []
        moves = self.move_ids.filtered(lambda m: m.quantity or m.product_uom_qty)
        for index, move in enumerate(moves, start=1):
            mls = move.move_line_ids
            qty = sum(
                ml.product_uom_id._compute_quantity(
                    ml.quantity, move.product_id.uom_id, round=False
                )
                for ml in mls
            )
            if not qty:
                qty = move.product_uom._compute_quantity(
                    move.quantity or move.product_uom_qty,
                    move.product_id.uom_id,
                    round=False,
                )
            subtotal = sum(mls.mapped("l10n_ro_price_subtotal"))
            charges = sum(mls.mapped("l10n_ro_additional_charges"))
            tax = sum(mls.mapped("l10n_ro_price_tax"))
            # Packages are expressed in the move's packaging UoM when it
            # differs from the product UoM, falling back to the product's own
            # packaging (the first secondary ``uom_ids``).
            packaging_uom = move.packaging_uom_id
            if not packaging_uom or packaging_uom == move.product_id.uom_id:
                packaging_uom = move.product_id.uom_ids[:1]
            packages = 0.0
            if packaging_uom and packaging_uom != move.product_id.uom_id:
                packages = move.product_id.uom_id._compute_quantity(
                    qty, packaging_uom, round=False
                )
            currency = mls[:1].l10n_ro_currency_id or self.company_id.currency_id
            # Subtotal = goods value + landed charges (net, excl. VAT);
            # Total = subtotal + VAT.
            net = subtotal + charges
            lines.append(
                {
                    "move": move,
                    "position": index,
                    "product": move.product_id,
                    "code": move.product_id.default_code or "",
                    "name": move.product_id.name,
                    "uom": move.product_id.uom_id,
                    "quantity": qty,
                    "currency": currency,
                    "price_unit": (subtotal / qty) if qty else 0.0,
                    "purchase_value": subtotal,
                    "packages": packages,
                    "packaging_uom": packaging_uom if packages else False,
                    "additional_charges": charges,
                    "subtotal": net,
                    "tax": tax,
                    "total": net + tax,
                    "weight": move.product_id.weight * qty,
                }
            )
        return lines

    def _l10n_ro_aviz_report_lines(self):
        """Build the aviz (delivery note) rows for a RO outgoing/internal
        picking: one row per move with JPB's columns (PLU, code, EAN, UoM,
        quantity, unit price and value), quantities in the product's reference
        UoM and amounts from the valued move lines. No packaging column."""
        self.ensure_one()
        lines = []
        moves = self.move_ids.filtered(lambda m: m.quantity or m.product_uom_qty)
        for index, move in enumerate(moves, start=1):
            mls = move.move_line_ids
            qty = sum(
                ml.product_uom_id._compute_quantity(
                    ml.quantity, move.product_id.uom_id, round=False
                )
                for ml in mls
            )
            if not qty:
                qty = move.product_uom._compute_quantity(
                    move.quantity or move.product_uom_qty,
                    move.product_id.uom_id,
                    round=False,
                )
            value = sum(mls.mapped("l10n_ro_price_subtotal"))
            currency = mls[:1].l10n_ro_currency_id or self.company_id.currency_id
            lines.append(
                {
                    "position": index,
                    "product": move.product_id,
                    "plu": getattr(move.product_id, "plu_code", "") or "",
                    "code": move.product_id.default_code or "",
                    "ean": move.product_id.barcode or "",
                    "name": move.product_id.name,
                    "uom": move.product_id.uom_id,
                    "quantity": qty,
                    "currency": currency,
                    "price_unit": (value / qty) if qty else 0.0,
                    "value": value,
                }
            )
        return lines

    def _l10n_ro_nir_doc_info(self):
        """Source document of the receipt and, for a foreign-currency purchase
        order, the order total and its exchange rate booked in RON.

        The vendor bill is not required: the reference is the picking origin
        (the PO name), and the currency/rate line is shown only when the
        purchase order is in a currency other than the company's."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        info = {
            "origin": self.origin or "",
            "currency": company_currency,
            "foreign": False,
            "amount": 0.0,
            "rate": 0.0,
        }
        po = self.purchase_id if "purchase_id" in self._fields else False
        if po and po.currency_id and po.currency_id != company_currency:
            date = self.date_done or self.scheduled_date
            date = date.date() if date else fields.Date.context_today(self)
            info.update(
                {
                    "foreign": True,
                    "currency": po.currency_id,
                    "amount": po.amount_total,
                    "rate": po.currency_id._convert(
                        1.0, company_currency, self.company_id, date
                    ),
                }
            )
        return info

    def _l10n_ro_show_valued_columns(self):
        """Whether the plain valued columns belong on this picking's slip.

        A more specific layout - the retail reception note - replaces the
        valued money columns (unit price, additional charges, subtotal, taxes,
        total) with its own cost/markup/shelf-price columns and turns this off,
        so the two do not both print and leave the table with two sets of money
        columns. Base behaviour follows the outgoing-aviz price setting, so no
        value columns print on an aviz issued without prices; the retail
        picking report overrides this."""
        self.ensure_one()
        return self._l10n_ro_show_aviz_prices()

    def _l10n_ro_show_aviz_prices(self):
        """Whether the price/value columns print on this slip.

        The outgoing delivery note (aviz de însoțire a mărfii) is a transport
        document that may be issued with or without prices; the company setting
        ``l10n_ro_print_aviz_with_prices`` decides. Only outgoing pickings are
        affected: the reception note (NIR) and internal transfers always keep
        their value columns."""
        self.ensure_one()
        if self.picking_type_id.code == "outgoing":
            return self.company_id.l10n_ro_print_aviz_with_prices
        return True

    def _get_report_lang(self):
        """Print the stock documents of a Romanian company in Romanian.

        The delivery slip (NIR, aviz, bon de consum) is rendered in the
        partner's language, so a receipt from a foreign vendor, or a
        partnerless internal transfer or consume voucher, comes out in English.
        For a Romanian company these are legal documents that must read
        Romanian. ``ir.actions.report`` flags the render of this one report with
        ``l10n_ro_force_picking_report_lang``; we honour the flag here so every
        other report, and every non-RO company, keeps the partner's language.
        The Romanian language has to be installed, otherwise rendering with it
        raises ``Invalid language code`` - a RO company without it keeps the
        partner's language rather than crashing the slip."""
        lang = super()._get_report_lang()
        if (
            self.env.context.get("l10n_ro_force_picking_report_lang")
            and self.company_id.country_id.code == "RO"
            and any(
                code == "ro_RO" for code, _name in self.env["res.lang"].get_installed()
            )
        ):
            return "ro_RO"
        return lang

    def _compute_l10n_ro_is_internal(self):
        for pick in self:
            pick.l10n_ro_is_internal = pick.move_ids and not (
                pick.move_ids.mapped("sale_line_id")
                or pick.move_ids.mapped("purchase_line_id")
            )

    @api.depends(
        "state",
        "move_line_ids",
        "move_line_ids.quantity",
        "move_line_ids.l10n_ro_price_subtotal",
        "move_line_ids.l10n_ro_price_total",
    )
    def _compute_l10n_ro_valued_fields(self):
        for pick in self:
            pick.l10n_ro_currency_id = (
                pick.move_line_ids[0].l10n_ro_currency_id
                if pick.move_line_ids
                else pick.company_id.currency_id
            )
            pick.l10n_ro_amount_untaxed = 0
            pick.l10n_ro_amount_tax = 0
            pick.l10n_ro_amount_total = 0
            for line in pick.move_line_ids:
                pick.l10n_ro_amount_untaxed += line.l10n_ro_price_subtotal
                pick.l10n_ro_amount_tax += line.l10n_ro_price_tax
                pick.l10n_ro_amount_total += line.l10n_ro_price_total
