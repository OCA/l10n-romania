import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-l10n_ro_account_bank_statement_import_mt940_brd',
        'odoo8-addon-l10n_ro_config',
        'odoo8-addon-l10n_ro_partner_create_by_vat',
        'odoo8-addon-l10n_ro_partner_unique',
        'odoo8-addon-l10n_ro_siruta',
        'odoo8-addon-l10n_ro_vat_on_payment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
