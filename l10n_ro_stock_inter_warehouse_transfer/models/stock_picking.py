# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    l10n_ro_inter_wh_location_dest_id = fields.Many2one(
        "stock.location",
        string="Final Destination Location",
        help="The products will be automatically tranferred in this final location",
    )
    l10n_ro_inter_wh_location_dest_visible = fields.Boolean(
        compute="_compute_l10n_ro_inter_wh_location_dest_visible"
    )
    l10n_ro_transit_location = fields.Many2one(
        "stock.location",
        default=lambda self: self.env.ref(
            "l10n_ro_stock_inter_warehouse_transfer.stock_location_inter_wh"
        ),
        store=False,
    )

    @api.depends("location_dest_id")
    def _compute_l10n_ro_inter_wh_location_dest_visible(self):
        for pick in self:
            pick.l10n_ro_inter_wh_location_dest_visible = False
            if pick.is_l10n_ro_record:
                pick.l10n_ro_inter_wh_location_dest_visible = (
                    pick.is_l10n_ro_record
                    and pick.location_dest_id == pick.l10n_ro_transit_location
                )

    def _action_done(self):
        res = super()._action_done()
        for picking in self.filtered("is_l10n_ro_record"):
            if picking.state == "done":
                inter_wh_transit_loc = self.env.ref(
                    "l10n_ro_stock_inter_warehouse_transfer.stock_location_inter_wh"
                )
                src_company = (
                    picking.mapped("move_lines.location_id.company_id") or None
                )
                if (
                    picking.location_dest_id == inter_wh_transit_loc
                    and picking.l10n_ro_inter_wh_location_dest_id
                ):

                    dest_company = (
                        picking.l10n_ro_inter_wh_location_dest_id
                        and picking.l10n_ro_inter_wh_location_dest_id.company_id
                        or None
                    )

                    if src_company and dest_company and src_company != dest_company:
                        assert len(src_company) == 1
                        assert len(dest_company) == 1

                        next_pick = None
                        wh2_stock_loc = picking.l10n_ro_inter_wh_location_dest_id
                        wh_dest = self.env["stock.warehouse"].search(
                            [
                                (
                                    "lot_stock_id",
                                    "=",
                                    wh2_stock_loc.id,
                                )
                            ]
                        )
                        # creare picking RO Transit -> WH2/Stock
                        for mv in picking.move_lines:
                            dest_mv = mv.sudo().copy(
                                {
                                    "location_id": inter_wh_transit_loc.id,
                                    "location_dest_id": wh2_stock_loc.id,
                                    "picking_type_id": wh_dest.in_type_id.id,  # receipt
                                    "picking_id": None,
                                    "company_id": dest_company.id,
                                }
                            )
                            dest_mv.sudo().with_company(
                                dest_company.id
                            )._assign_picking()
                            mv.move_dest_ids = [(6, 0, dest_mv.ids)]
                            next_pick = dest_mv.picking_id

                        if next_pick:
                            # pentru move-urile WH1/Stoc -> RO transit s-au
                            # facut 2 SVL, unul cu +qty, altul cu -qty
                            #
                            # move-ul urmator celui din svl cu +qty ar trebuie
                            # sa fie tratat ca si intrare in WH2
                            # setez price_unit pentru move, ca si cum ar proveni
                            # dintr-o # receptie

                            svls_plus = (
                                picking.sudo()
                                .mapped("move_lines.stock_valuation_layer_ids")
                                .filtered(lambda svl: svl.quantity > 0)
                            )
                            for svl_plus in svls_plus:
                                dest_move = svl_plus.stock_move_id.move_dest_ids
                                if dest_move:
                                    dest_move.sudo().price_unit = svl_plus.unit_cost

                            next_pick.sudo().with_company(
                                dest_company.id
                            ).action_confirm()
                            next_pick.sudo().with_company(
                                dest_company.id
                            ).action_assign()
                            for ml in next_pick.move_line_ids:
                                ml.qty_done = ml.product_qty

                            # actualizez standard price aici, deoarece
                            # StockMove.product_price_update_before_done()
                            # actualizeaza standard_price doar pentru cele is_in()
                            # si cele din next_pick sunt is_internal()
                            for mv in next_pick.move_lines:
                                mv.l10n_ro_inter_wh_product_price_update_before_done()

                            next_pick.sudo().with_company(
                                dest_company.id
                            ).button_validate()

                            # pentru SVL cu qty > 0
                            # schimb compania si
                            # stock_move_id = svl.stock_move_id.move_dest_ids
                            # pentru ca sa apara in stock sheet report
                            # pentru compania dest_company
                            for svl_plus in svls_plus:
                                dest_move = svl_plus.stock_move_id.move_dest_ids
                                svl_plus.sudo().write(
                                    {
                                        "company_id": dest_company.id,
                                        "stock_move_id": dest_move
                                        and dest_move[0].id
                                        or None,
                                    }
                                )
        return res
