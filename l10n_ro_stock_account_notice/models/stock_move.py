# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_ro_notice = fields.Boolean(
        related="picking_id.l10n_ro_notice",
        help="field form picking, just to be used in view",
    )

    @api.onchange("product_id", "product_uom_qty")
    def _onchange_product_id(self):
        "if delivery notice we are going to put the price for partner"
        if (
            self.is_l10n_ro_record
            and self.picking_id.l10n_ro_notice
            and self.product_id
            and not self.price_unit
        ):
            # if you set a price we are not changing it anymore
            # maybe in context with partner ..
            self.price_unit = self.product_id.with_company(self.company_id).lst_price

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        if not self.filtered("is_l10n_ro_record"):
            return valued_types

        valued_types += [
            "reception_notice",  # receptie de la furnizor cu aviz
            "reception_notice_return",  # retur receptie de la furnizor cu aviz
            "delivery_notice",
            "delivery_notice_return",
        ]
        return valued_types

    def _is_reception(self):
        """Este receptie in stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception()

        it_is = (
            super(StockMove, self)._is_reception()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_reception_return(self):
        """Este un retur la o receptie in stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception_return()

        it_is = (
            super(StockMove, self)._is_reception_return()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_reception_notice(self):
        """Este receptie in stoc cu aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception_return()

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_notice_svl(self, forced_quantity=None):
        created_svl_ids = self.env["stock.valuation.layer"]
        for move in self.with_context(standard=True, valued_type="reception_notice"):

            if (
                move.product_id.type != "product"
                or move.product_id.valuation != "real_time"
            ):
                continue
            picking = move.picking_id
            date = picking.l10n_ro_accounting_date or picking.date
            price_unit = move.price_unit
            qty = move.quantity_done
            value = qty * price_unit
            product = move.product_id

            accounts = move.with_context(
                valued_type="invoice_in_notice"
            )._get_accounting_data_for_valuation()
            bill_to_recieve = move.company_id.l10n_ro_property_bill_to_receive.id
            if not bill_to_recieve:
                raise ValidationError(
                    _(
                        "Go to Settings/config/romania and set the property bill to receive to 408."
                    )
                )
            account_move = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "date": date,
                        "ref": f"Reception Notice for picking=({picking.name},{picking.id}), product={product.id,product.name}",
                        "journal_id": accounts[0],
                        "stock_move_id": move.id,
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "account_id": accounts[3],  # 3xx
                                    "product_id": product.id,
                                    "name": product.name
                                    + f" ({price_unit}x{qty}={value})",
                                    "quantity": qty,
                                    "debit": value,
                                    "credit": 0,
                                    "price_unit": value / qty if qty else 0,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "account_id": bill_to_recieve,
                                    "product_id": product.id,
                                    "name": product.name
                                    + f" ({price_unit}x{qty}={value})",
                                    "quantity": qty,
                                    "debit": 0,
                                    "credit": value,
                                    "price_unit": value / qty if qty else 0,
                                },
                            ),
                        ],
                    }
                )
            )
            account_move.action_post()
            svl = self.env["stock.valuation.layer"].create(
                {
                    "description": f"Notice reception picking=({picking.name},{picking.id})",
                    "account_move_id": account_move.id,
                    "stock_move_id": move.id,
                    "product_id": move.product_id.id,
                    "company_id": move.company_id.id,
                    "value": value,
                    "remaining_value": value,
                    "l10n_ro_bill_accounting_date": date,
                    "quantity": qty,
                    "remaining_qty": qty,
                    "unit_cost": price_unit,
                    "l10n_ro_valued_type": "reception_notice",
                }
            )

            created_svl_ids |= svl

        return created_svl_ids

    def _is_reception_notice_return(self):
        """Este un retur la receptie in stoc cu aviz"""
        if not self.is_l10n_ro_record:
            return False

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_notice_return_svl(self, forced_quantity=None):
        svl = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(
                standard=True, valued_type="reception_notice_return"
            )
            if (
                move.origin_returned_move_id
                and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
            ):
                move = move.with_context(
                    origin_return_candidates=move.origin_returned_move_id.sudo()
                    .stock_valuation_layer_ids.filtered(lambda sv: sv.remaining_qty > 0)
                    .ids
                )
            created_svl = move._create_out_svl(forced_quantity)
            # we must also create a account_move for what was returned
            picking = move.picking_id
            product = created_svl.product_id
            accounts = product._get_product_accounts()
            accoutns2 = move._get_accounting_data_for_valuation()
            created_account_move = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "date": move.date,
                        "ref": f"Return for notice_reception picking=({picking.name},{picking.id}), product={product.id,product.name}",
                        "journal_id": accoutns2[0],
                        "stock_move_id": move.id,
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "account_id": accounts["stock_valuation"].id,  # 3xx
                                    "product_id": product.id,
                                    "name": "Return for notice_reception"
                                    + f" qty={created_svl.quantity} value={created_svl.value}",
                                    "quantity": created_svl.quantity,
                                    "debit": 0,
                                    "credit": abs(created_svl.value),
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "account_id": accounts["income"].id,  # 7xx
                                    "product_id": product.id,
                                    "name": "Return for notice_reception"
                                    + f" qty={created_svl.quantity} value={created_svl.value}",
                                    "quantity": created_svl.quantity,
                                    "debit": abs(created_svl.value),
                                    "credit": 0,
                                },
                            ),
                        ],
                    }
                )
            )
            created_account_move.action_post()
            created_svl.account_move_id = created_account_move.id
            svl += created_svl
        return svl

    def _is_delivery(self):
        """Este livrare din stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_delivery()
        return (
            super(StockMove, self)._is_delivery() and not self.picking_id.l10n_ro_notice
        )

    def _is_delivery_return(self):
        """Este retur la o livrare din stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_delivery_return()

        it_is = (
            super(StockMove, self)._is_delivery_return()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_delivery_notice(self):
        """Este livrare cu aviz"""
        if not self.is_l10n_ro_record:
            return False

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )
        return it_is

    def _create_delivery_notice_svl(self, forced_quantity=None):
        moves = self.with_context(standard=True, valued_type="delivery_notice")
        svls = self.env["stock.valuation.layer"]
        for move in moves:
            created_svl = move._create_out_svl(forced_quantity)
            picking = self.picking_id
            product = move.product_id
            accounts = product._get_product_accounts()
            accounts2 = move._get_accounting_data_for_valuation()
            value = abs(created_svl.value)
            qty = abs(created_svl.quantity)
            date = (
                picking.l10n_ro_accounting_date
                if picking.l10n_ro_accounting_date
                else move.date
            )
            inv_to_create_acc = move.company_id.l10n_ro_property_invoice_to_create
            if not inv_to_create_acc:
                raise ValidationError(
                    _(
                        "Go to Settings/config/romania and set the property bill to receive to 418."
                    )
                )
            # O entitate livreaza produse finite doar pe baza de aviz de insotire a marfii.
            # Ulterior se intocmeste factura.
            # Valoarea facturii este de 300.000 lei plus TVA 19%. Costul de productie este de 85.000 lei.
            # Livrare produse finite:
            # 418 = 701         300.000 lei
            # Descarcare de gestiune:
            # 711 = 345            85.000 lei
            # Emiterea facturii:
            # 4111 = %        357.000 lei
            #        418     300.000 lei
            #         4427      57.000 lei
            created_account_move = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "date": date,
                        "ref": f"Delivery Notice for picking=({picking.name},{picking.id}), product={product.id,product.name}",
                        "journal_id": accounts2[0],
                        "stock_move_id": move.id,
                        "line_ids": [
                            # move_lines with prices from notice
                            # notice delivery at sale price ( livrarea de produse)
                            (
                                0,
                                0,
                                {
                                    "partner_id": move.partner_id.id,
                                    "account_id": inv_to_create_acc.id,  # 418
                                    "product_id": product.id,
                                    # do not change the name because is used when making the invoice
                                    "name": "delivery_price "
                                    + product.name
                                    + f" ({move.price_unit}x{qty})",
                                    "quantity": qty,
                                    "debit": move.price_unit * qty,
                                    "credit": 0,
                                    "price_unit": move.price_unit,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "partner_id": move.partner_id.id,
                                    "account_id": accounts["income"].id,  # 7xx
                                    "product_id": product.id,
                                    "name": "delivery_price "
                                    + product.name
                                    + f" ({move.price_unit}x{qty})",
                                    "quantity": qty,
                                    "debit": 0,
                                    "credit": move.price_unit * qty,
                                    "price_unit": move.price_unit,
                                },
                            ),
                            # what was taken out of stock ( at existing values)
                            # descarcarea de gestiune
                            (
                                0,
                                0,
                                {
                                    "partner_id": move.partner_id.id,
                                    "account_id": accounts["income"].id,  # 7xx
                                    "product_id": product.id,
                                    "name": "cost price "
                                    + product.name
                                    + f" qty={qty}, value={value})",
                                    "quantity": qty,
                                    "debit": value,
                                    "credit": 0,
                                    "price_unit": value / qty if qty else 0,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "partner_id": move.partner_id.id,
                                    "account_id": accounts["stock_valuation"].id,  # 3xx
                                    "product_id": product.id,
                                    "name": "cost price "
                                    + product.name
                                    + f" qty={qty}, value={value})",
                                    "quantity": qty,
                                    "debit": 0,
                                    "credit": value,
                                    "price_unit": value / qty if qty else 0,
                                },
                            ),
                        ],
                    }
                )
            )
            created_account_move.action_post()
            created_svl.write(
                {
                    "l10n_ro_bill_accounting_date": date,
                    "account_move_id": created_account_move,
                }
            )
            svls |= created_svl
        return svls

    def _is_delivery_notice_return(self):
        """Este retur livrare cu aviz"""
        if not self.is_l10n_ro_record:
            return False
        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_notice_return_svl(self, forced_quantity=None):
        moves = self.with_context(standard=True, valued_type="delivery_notice_return")
        svls = self.env["stock.valuation.layer"]
        for move in moves:
            created_svl = move._create_in_svl(forced_quantity)
            picking = self.picking_id
            product = move.product_id
            qty = abs(created_svl.quantity)
            date = (
                picking.l10n_ro_accounting_date
                if picking.l10n_ro_accounting_date
                else move.date
            )
            # the accounting move must be inverse of the original one with this qty
            origin_returned_move_id = move.origin_returned_move_id
            origin_account_id = origin_returned_move_id.account_move_ids
            # we can find origin_account_id in svl ( to work before of this version but are not ok, so it does not mater)
            if len(origin_account_id) != 1:
                raise ValidationError(
                    _(
                        f"For stock_move={move}, with origin_returned_move_id={origin_returned_move_id}"
                        f" the origin_account_id={origin_account_id} and because it's len is not 1"
                        f" we can not create reverse accounting entries"
                    )
                )
            account_move_dict = {
                "date": date,
                "ref": f"Return for {origin_account_id.id},{origin_account_id.name}. Return of Delivery Notice for picking=({picking.name},{picking.id}), product={product.id,product.name}",
                "journal_id": origin_account_id.journal_id.id,
                "stock_move_id": move.id,
                "line_ids": [],
            }
            for line in origin_account_id.line_ids:
                multiplier = qty / line.quantity if line.quantity else 0
                account_move_dict["line_ids"].append(
                    [
                        0,
                        0,
                        {
                            "partner_id": line.partner_id.id,
                            "account_id": line.account_id.id,
                            "product_id": line.product_id.id,
                            "name": "Return of: " + line.name,
                            "quantity": qty,
                            "debit": line.debit * multiplier,
                            "credit": line.credit * multiplier,
                            "price_unit": line.price_unit * multiplier,
                        },
                    ]
                )
            created_account_move = (
                self.env["account.move"].sudo().create(account_move_dict)
            )
            created_account_move.post()
            created_svl.write(
                {
                    "l10n_ro_bill_accounting_date": date,
                    "account_move_id": created_account_move,
                }
            )
            svls |= created_svl
        return svls

    def _account_entry_move(self, qty, description, svl_id, cost):
        if self.picking_id.l10n_ro_notice and self.env["stock.valuation.layer"].browse(
            svl_id
        ).l10n_ro_valued_type in ["delivery_notice", "delivery_notice_return"]:
            # we done the journal entry in same time as svl
            return
        else:
            return super()._account_entry_move(qty, description, svl_id, cost)

    def _get_accounting_data_for_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super(
            StockMove, self
        )._get_accounting_data_for_valuation()
        if (
            self.is_l10n_ro_record
            and self.product_id.categ_id.l10n_ro_stock_account_change
        ):
            location_from = self.location_id
            location_to = self.location_dest_id
            valued_type = self.env.context.get("valued_type", "indefinite")

            # in nir si factura se ca utiliza 408
            if valued_type == "invoice_in_notice":
                if location_to.l10n_ro_property_account_expense_location_id:
                    acc_dest = (
                        acc_valuation
                    ) = location_to.l10n_ro_property_account_expense_location_id.id
                # if location_to.property_account_expense_location_id:
                #     acc_dest = (
                #         acc_valuation
                #     ) = location_to.property_account_expense_location_id.id
            elif valued_type == "invoice_out_notice":
                if location_to.l10n_ro_property_account_income_location_id:
                    acc_valuation = acc_dest
                    acc_dest = (
                        location_to.l10n_ro_property_account_income_location_id.id
                    )
                if location_from.l10n_ro_property_account_income_location_id:
                    acc_valuation = (
                        location_from.l10n_ro_property_account_income_location_id.id
                    )

            # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
            elif valued_type in [
                "delivery_notice",
            ]:
                acc_dest = (
                    location_from.l10n_ro_property_account_expense_location_id.id
                    or acc_dest
                )
            elif valued_type in [
                "delivery_notice_return",
            ]:
                acc_src = (
                    location_to.l10n_ro_property_account_expense_location_id.id
                    or acc_src
                )
        return journal_id, acc_src, acc_dest, acc_valuation
