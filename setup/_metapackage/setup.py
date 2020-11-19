import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-l10n-romania",
    description="Meta package for oca-l10n-romania Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-l10n_ro_account_period_close',
        'odoo14-addon-l10n_ro_address_extended',
        'odoo14-addon-l10n_ro_city',
        'odoo14-addon-l10n_ro_config',
        'odoo14-addon-l10n_ro_partner_create_by_vat',
        'odoo14-addon-l10n_ro_partner_unique',
        'odoo14-addon-l10n_ro_stock',
        'odoo14-addon-l10n_ro_vat_on_payment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
