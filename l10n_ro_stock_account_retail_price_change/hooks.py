# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def post_init_hook(env):
    """Give every existing company its own Proces Verbal series."""
    env["res.company"].search([])._l10n_ro_create_retail_price_change_sequence()
