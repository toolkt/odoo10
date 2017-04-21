# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp

from odoo.http import request

from fabric.api import *
import paramiko
import socket
import os
import glob



#@parallel
def file_send(localpath,remotepath):
    with settings(warn_only=True):
        put(localpath,remotepath,use_sudo=True)

#@parallel
def file_get(remotepath, localpath):
    get(remotepath,localpath)

#@parallel
def transfer_files(remotepath, localpath):
    remote = "%s/outbound" % remotepath
    get(remote,localpath)
    mv = "mv %s/outbound/* %s/transferred" % (remotepath,remotepath)
    sudo(mv)




class DmpiPlant(models.Model):
    _name = 'dmpi.plant'


    def _get_session_id(self):
    	print "-----------SESSION-------------"
    	session = request.session.uid
    	print request.httprequest.session.sid
    	#1b42f496ae1da9806c4086a4dfd319a8fb482e59
    	#1b42f496ae1da9806c4086a4dfd319a8fb482e59
    	#ad02d6a24113c1005b9bab73d973cc55f2c33657
    	#3eb4ab98b6cc9384376d43de2c9d9b83a8c8ea2a
    #session = fields.Char('Session', compute='_get_session_id')


    name = fields.Char('Plant')
    description = fields.Char('Description')



class DmpiDistPoAllocation(models.Model):
    _name = 'dmpi.dist.po.allocation'

    name = fields.Char("Description")
    date_start = fields.Date('Date Start')
    date_end = fields.Date('Date End')
    database_id = fields.Many2one('res.distributor.database','Database')
    active = fields.Boolean('Active', default=True)
    allocation_line_ids = fields.One2many('dmpi.dist.po.allocation.line','allocation_id',"Allocation Line", copy=True)

class DmpiDistPoAllocationLine(models.Model):
    _name = 'dmpi.dist.po.allocation.line'

    product_id = fields.Many2one('product.product','SKU')
    plant_id = fields.Many2one('dmpi.plant','Plant')
    allocation = fields.Float('Allocation')
    allocation_id = fields.Many2one('dmpi.dist.po.allocation','Allocation ID', on_delete='restrict')
    deliver_source = fields.Selection([('off_shore','Off Shore'),('inland','Inland')], 'Source')
    critical = fields.Boolean('Critical')

    #MOVED TO PRODUCT TEMPLATE
    #cases_pa = fields.Float('Cases per Pallet')
    #cases_cv = fields.Float('Cases per CV')
    #cases_tw = fields.Float('Cases per 10 Wheeler')
    #critical = fields.Boolean('Critical') 
    #weight = fields.Float('Weight')
    
class StockReturnReason(models.Model):
    _name = 'stock.return.reason'
    _description = 'Reason for Return'

    name = fields.Char('Return Reason', size=64, required=True)
    code = fields.Char('Code', size=64, required=True)
    return_type = fields.Selection([('GS','GS'),('BO','BO')], string='Return Type')



class product_template(models.Model):
    _inherit = 'product.template'

    deliver_source = fields.Selection([('off_shore','Off Shore'),('inland','Inland')], 'Source')
    cases_pa = fields.Float('Cases/Pallet')
    cases_cv = fields.Float('Cases/CV')
    cases_tw = fields.Float('Cases/10w')


class DmpiProductPricelist(models.Model):
    _name = 'dmpi.product.pricelist'

    name = fields.Char("Pricelist")
    date_start = fields.Date("Start Date")
    date_end = fields.Date("End Date")
    active = fields.Boolean("Active")
    type = fields.Selection([('sale','Sale'),('purchase','Purchase')], 'Type')
    items = fields.One2many('dmpi.product.pricelist.item','pricelist_id','Items', copy=True)

class DmpiProductPricelistItem(models.Model):
    _name = 'dmpi.product.pricelist.item'

    sequence = fields.Integer('Sequence', default=5)
    product_id = fields.Many2one('product.product','Product')
    unit_price = fields.Float("Unit Price")
    default = fields.Boolean("Default")
    pricelist_id = fields.Many2one('dmpi.product.pricelist','Pricelist')






    