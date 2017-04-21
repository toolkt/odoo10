# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp

import xmlrpclib
import psycopg2
import numbers
import decimal
import os


import odoorpc

ODOO_MODULES_DIR = '/tmp/modules/'

class ResDistributorDatabaseCommands(models.TransientModel):
    _name = "res.distributor.database.commands"
    _description = "Distributor Database Commands"

    @api.multi
    def restart_database(self):
        context = dict(self._context or {})
        print "SELECTED IDS:",context.get('active_ids')
        return {'type': 'ir.actions.act_window_close'}



class ResDistributorDatabaseModule(models.Model):
    _name = "res.distributor.database.module"

    #@api.multi
    #def write(self, vals):
    #    if vals.get('module'):
    #    return super(ResDistributorDatabaseModule, self).write(vals)

    @api.multi
    def create_file(self):
        directory = ODOO_MODULES_DIR
        if not os.path.exists(directory):
            os.makedirs(directory)

        for rec in self:
            if rec.module:
                path = '%s%s.zip' % (directory,rec.name)
                with open(path, "wb") as fh:
                    fh.write(rec.module.decode('base64'))         

    name = fields.Char('Technical Name')
    live = fields.Boolean('Live')
    description = fields.Char('Description')
    module = fields.Binary('Module (Zip)', attachment=True)





