A till attached to a shop whose goods are kept at the shelf price has to sell
the way that shop keeps its books. This module makes it do so: a point of sale
whose operation type belongs to a retail warehouse takes over that warehouse's
fiscal position and its retail price list.

The fiscal position is what carries both halves of the setup. It maps the taxes
the shelf price is split with - to the VAT included variants a till works with -
and it maps the accounts the goods, the markup and the deferred VAT are kept on,
so a shop that holds its merchandise on 371.01 rather than 371 has its sales
land there too.

Only fields left empty are filled, on creation and when this module is
installed, so a till deliberately run on another price list keeps it.

## A note for the migration to 20.0

This module exists only because of where the pieces sit in the dependency graph.
`l10n_ro_pos` depends on `point_of_sale` and `l10n_ro_config`, not on
`l10n_ro_stock_account_retail`, so it cannot read the retail marking of a
warehouse - and demo data of one module cannot reference records of a module
that is not among its dependencies.

Making `l10n_ro_pos` depend on `l10n_ro_stock_account_retail` would be the wrong
fix: a cash register does not need the accounting of goods held at retail in
order to work. When the dependencies are reworked for 20.0, the better move is
to push the marking of a shop down to where the point of sale can already see
it - `l10n_ro_retail`, the retail price list and the fiscal position of the
warehouse belong with the warehouse itself, in `l10n_ro_stock`, leaving only the
valuation of the markup and the deferred VAT in `l10n_ro_stock_account_retail`.
This bridge then has nothing left to bridge and can be dropped.
