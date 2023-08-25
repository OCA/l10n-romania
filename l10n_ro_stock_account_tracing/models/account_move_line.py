from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ro_stock_move_id = fields.Many2one(
        "stock.move",
        compute="_compute_stock_relation",
        store=True,
        string="Romania Stock Move",
    )
    l10n_ro_stock_picking_id = fields.Many2one(
        "stock.picking",
        compute="_compute_stock_relation",
        store=True,
        string="Romania Picking",
    )
    l10n_ro_stock_picking_type_id = fields.Many2one(
        "stock.picking.type",
        compute="_compute_stock_relation",
        store=True,
        string="Romania Picking Type",
    )
    l10n_ro_location_id = fields.Many2one(
        "stock.location",
        compute="_compute_stock_relation",
        store=True,
        string="Romania Source Location",
    )
    l10n_ro_location_dest_id = fields.Many2one(
        "stock.location",
        compute="_compute_stock_relation",
        store=True,
        string="Romania Destionation Location",
    )
    l10n_ro_product_category_id = fields.Many2one(
        "product.category",
        related="product_id.categ_id",
        store=True,
        string="Romania Product Category",
    )
    l10n_ro_valued_type = fields.Char(
        compute="_compute_stock_relation", store=True, string="Romania Valued Type"
    )
    l10n_ro_link_stock_move_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="account_move_line_stock_move_link",
        column1="account_move_line_id",
        column2="stock_move_id",
        string="Romania Stock Move Related",
    )

    def _getAmlData(self, stock_move):
        # Fixing on Return Products
        retur_all = stock_move.mapped("group_id.stock_move_ids.origin_returned_move_id")
        ret_ids = retur_all.ids
        move_type = self.mapped("move_id.move_type")
        # limit stock move just for income/outcome/return moves.
        if "out_refund" in move_type or "in_refund" in move_type:
            stock_move = stock_move.filtered(lambda x: x.id in ret_ids)
        else:
            stock_move = stock_move.filtered(lambda x: x.id not in ret_ids)
        vtype = stock_move.mapped("stock_valuation_layer_ids.l10n_ro_valued_type")
        stock_picking_id = stock_move.picking_id
        location_id = stock_move.location_id
        location_dest_id = stock_move.location_dest_id
        valued_type = vtype and vtype[0] or ""
        stock_picking_type_id = stock_picking_id.picking_type_id
        return (
            stock_picking_id,
            location_id,
            location_dest_id,
            valued_type,
            stock_picking_type_id,
        )

    @api.depends("move_id", "move_id.state", "move_id.stock_move_id")
    def _compute_stock_relation(self):
        for s in self:
            stock_picking_id = (
                location_id
            ) = location_dest_id = valued_type = stock_picking_type_id = None
            if s.move_id.stock_move_id:
                (
                    stock_picking_id,
                    location_id,
                    location_dest_id,
                    valued_type,
                    stock_picking_type_id,
                ) = self._getAmlData(s.move_id.stock_move_id)
            s.update(
                {
                    "l10n_ro_stock_picking_id": stock_picking_id
                    and stock_picking_id.id,
                    "l10n_ro_location_id": location_id and location_id.id,
                    "l10n_ro_location_dest_id": location_dest_id
                    and location_dest_id.id,
                    "l10n_ro_valued_type": valued_type,
                    "l10n_ro_stock_picking_type_id": stock_picking_type_id
                    and stock_picking_type_id.id,
                }
            )

    def setStockMoveData(self, stock_move):
        stock_picking_id = (
            location_id
        ) = location_dest_id = valued_type = stock_picking_type_id = None
        if stock_move:
            (
                stock_picking_id,
                location_id,
                location_dest_id,
                valued_type,
                stock_picking_type_id,
            ) = self._getAmlData(stock_move)
        self.update(
            {
                "l10n_ro_stock_picking_id": stock_picking_id and stock_picking_id.id,
                "l10n_ro_location_id": location_id and location_id.id,
                "l10n_ro_location_dest_id": location_dest_id and location_dest_id.id,
                "l10n_ro_valued_type": valued_type,
                "l10n_ro_stock_picking_type_id": stock_picking_type_id
                and stock_picking_type_id.id,
            }
        )


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            invoice_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            for line in invoice_lines:
                valuation_stock_moves = line._l10n_ro_get_valuation_stock_moves()
                if valuation_stock_moves:
                    line.setStockMoveData(valuation_stock_moves[-1])
        return res
