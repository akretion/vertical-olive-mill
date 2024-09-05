# Copyright 2024 Barroux Abbey
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copied and adapted from the OCA module intrastat_product

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.m2o_to_x2m(
        env.cr,
        env["olive.oil.production"],
        "olive_oil_production",
        "palox_ids",
        openupgrade.get_legacy_name("palox_id"),
        )
    env["olive.oil.production"].search([])._compute_palox_ids_str()
