# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 OdooERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    wh_consume_loc_id = fields.Many2one(
        'stock.location', 'Consume Location')
    wh_usage_loc_id = fields.Many2one(
        'stock.location', 'Usage Giving Location')
    consume_type_id = fields.Many2one(
        'stock.picking.type', 'Consume Type')
    usage_type_id = fields.Many2one(
        'stock.picking.type', 'Usage Giving Type')

    # Change warehouse methods for create to add the consume and usage giving
    # operations.

    @api.model
    def create(self, vals):
        warehouse = super(StockWarehouse, self).create(vals)
        stock_loc_obj = self.env['stock.location']
        wh_consume_loc_vals = {'name': _('Consume'),
                               'active': True,
                               'usage': 'consume',
                               'company_id': warehouse.company_id.id,
                               'location_id': warehouse.view_location_id.id}
        wh_usage_loc_vals = {'name': _('Usage'),
                             'active': True,
                             'usage': 'usage_giving',
                             'company_id': warehouse.company_id.id,
                             'location_id': warehouse.view_location_id.id}
        warehouse.wh_consume_loc_id = stock_loc_obj.create(
            wh_consume_loc_vals)
        warehouse.wh_usage_loc_id = stock_loc_obj.create(
            wh_usage_loc_vals)
        # Update picking types location destination with the locations created
        warehouse.consume_type_id.default_location_dest_id = \
            warehouse.wh_consume_loc_id
        warehouse.usage_type_id.default_location_dest_id = \
            warehouse.wh_usage_loc_id
        return warehouse

    @api.model
    def create_sequences_and_picking_types(self):
        warehouse_data = super(
            StockWarehouse, self).create_sequences_and_picking_types()
        warehouse = self
        seq_obj = self.env['ir.sequence']
        picking_type_obj = self.env['stock.picking.type']
        # create new sequences
        cons_seq_id = seq_obj.sudo().create(
            {'name': warehouse.name + _(' Sequence consume'),
             'prefix': warehouse.code + '/CONS/', 'padding': 5})
        usage_seq_id = seq_obj.sudo().create(
            {'name': warehouse.name + _(' Sequence usage'),
             'prefix': warehouse.code + '/USAGE/', 'padding': 5})

        wh_stock_loc = warehouse.lot_stock_id
        cons_stock_loc = warehouse.wh_consume_loc_id
        usage_stock_loc = warehouse.wh_usage_loc_id

        # order the picking types with a sequence allowing to have the
        # following suit for each warehouse: reception, internal, pick, pack,
        # ship.
        max_sequence = self.env['stock.picking.type'].search_read(
            [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        # choose the next available color for the picking types of this
        # warehouse
        color = 0
        # put flashy colors first
        available_colors = [c % 9 for c in range(3, 12)]
        all_used_colors = self.env['stock.picking.type'].search_read(
            [('warehouse_id', '!=', False), ('color', '!=', False)],
            ['color'], order='color')
        # don't use sets to preserve the list order
        for x in all_used_colors:
            if x['color'] in available_colors:
                available_colors.remove(x['color'])
        if available_colors:
            color = available_colors[0]

        consume_type_id = picking_type_obj.create(
            {'name': _('Consume'),
             'warehouse_id': warehouse.id,
             'code': 'internal',
             'sequence_id': cons_seq_id.id,
             'default_location_src_id': wh_stock_loc.id,
             'default_location_dest_id': cons_stock_loc.id,
             'sequence': max_sequence + 1,
             'color': color}
        )
        usage_type_id = picking_type_obj.create(
            {'name': _('Usage'),
             'warehouse_id': warehouse.id,
             'code': 'internal',
             'sequence_id': usage_seq_id.id,
             'default_location_src_id': wh_stock_loc.id,
             'default_location_dest_id': usage_stock_loc.id,
             'sequence': max_sequence + 4,
             'color': color}
        )
        vals = {'consume_type_id': consume_type_id.id,
                'usage_type_id': usage_type_id.id, }
        warehouse.write(vals)
        return warehouse_data
