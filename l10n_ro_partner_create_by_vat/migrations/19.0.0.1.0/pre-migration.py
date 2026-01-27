from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    _remove_views(env)


def _remove_views(env):
    """
    Remove views that might conflict with the new modules being installed.
    """
    views = [
        "l10n_ro_partner_create_by_vat.view_partner_create_by_vat_einvoice",
        "l10n_ro_partner_create_by_vat.view_partner_anaf_status_form",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)
