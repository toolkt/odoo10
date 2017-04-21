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


import odoorpc



class ResPartner(models.Model):
    _inherit = "res.partner"

    ship_to_code = fields.Char('Ship to Code')
    sold_to_code = fields.Char('Sold to Code')



class ResPartnerChannel(models.Model):
    _name = 'res.partner.channel'
    _description = 'Partner Channel'


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'].name+'/'+name
            res.append((record.id, name))
        return res


    channel_type = fields.Selection([('Grocery','Grocery'),('Food Service','Food Service'),('Catch All','Catch All')], string='Distributor Type', required=True)
    name = fields.Char(string='Channel Name', size=64, required=True)
    code = fields.Char(string='Channel Code', size=6, required=False)
    active = fields.Boolean(string='Active', default=lambda *a: 1)
    #heirarchy_id = fields.Many2one('res.partner.channel.heirarchy','Heirarchy', select=True, ondelete='restrict', domain="[('type','=','view')]")

    parent_id = fields.Many2one('res.partner.channel','Parent', select=True, ondelete='cascade', domain="[('type','=','normal')]")
    type = fields.Selection([('view','View'), ('normal','Normal')], 'Category Type', default='normal', help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure.")



class ResPartnerCoverage(models.Model):
    _name = 'res.partner.coverage'
    _description = 'Partner Coverage'

    name = fields.Char('Coverage Type', size=64, required=True)
    active = fields.Boolean('Active', default=lambda *a: 1)
    van_sale = fields.Boolean('Van Sales')

