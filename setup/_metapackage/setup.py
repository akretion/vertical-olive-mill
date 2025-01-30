import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-akretion-vertical-olive-mill",
    description="Meta package for akretion-vertical-olive-mill Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-l10n_fr_olive_mill',
        'odoo10-addon-olive_mill',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 10.0',
    ]
)
