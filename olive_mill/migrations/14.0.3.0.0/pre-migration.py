# Copyright 2024 Barroux Abbey
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # archive compensation tanks
    openupgrade.logged_query(
        env.cr,
        "UPDATE stock_location set olive_tank_type=null, "
        "olive_season_id=null, olive_season_year=null, oil_product_id=null, "
        "active=false WHERE olive_tank_type='compensation'")
