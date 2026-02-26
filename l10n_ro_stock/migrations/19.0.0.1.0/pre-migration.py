from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    _remove_views(env)


def _remove_views(env):
    """
    Remove views that might conflict with the new modules being installed.
    """
    views = [
        "l10n_ro_stock.view_location_form",
        "l10n_ro_stock.view_location_search",
        "l10n_ro_stock.view_location_tree2",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)
