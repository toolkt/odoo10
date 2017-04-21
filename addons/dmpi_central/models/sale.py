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


class RPCProxyOne(object):
    def __init__(self, server, resource):
        self.server = server
        common = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/2/common' % (self.server.remote_host,self.server.remote_port),verbose=True)
        self.uid = common.authenticate(self.server.db,self.server.xmlrpc_user,self.server.xmlrpc_pass, {})
        self.models = xmlrpclib.ServerProxy('http://%s:%d/xmlrpc/2/object' % (self.server.remote_host,self.server.remote_port),verbose=True)
        self.resource = resource

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.models.execute_kw(self.server.db, self.uid, self.server.xmlrpc_pass, self.resource, name, *args)
        #return lambda *args, **kwargs: self.rpc.execute(self.server['db'], self.uid, self.server['password'], self.resource, name, *args)

class RPCProxy(object):
    def __init__(self, server):
        self.server = server

    def get(self, resource):
        return RPCProxyOne(self.server, resource)


class DmpiDistributorMiddleware(models.Model):
    _name = "dmpi.distributor.middleware"

    name = fields.Char('Middleware')









class SaleOrder(models.Model):
    _inherit = 'sale.order'

    #self.env['ir.sequence']




    def create_sale(self, data):
        print data


        sold_partner_id = self.env['res.partner'].search([('sold_to_code','=',data['sold_to_code'])],limit=1)
        ship_partner_id = self.env['res.partner'].search([('ship_to_code','=',data['ship_to_code'])],limit=1)

        new_so = self.env['sale.order'].create({
            'partner_id': sold_partner_id.id,
            'partner_invoice_id': sold_partner_id.id,
            'partner_shipping_id': ship_partner_id.id,
            'dist_db': data['dist_db'],
            'dist_po_id': data['dist_po_id'],
            'status': 'submitted',
            'order_line' : data['lines']
            })

        print new_so
        if new_so:
            so_details = {
                'success' : True,
                'odoo_po_no' : new_so.odoo_po_no,
                'central_so_id': new_so.id,
            }        

        else:
            so_details = {
                'success' : False,
            }   

        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for (_, p) in self.products.iteritems()],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        """

        return so_details




    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['odoo_po_no'] = self.env['ir.sequence'].next_by_code('dmpi.odoo.po.number')
        return super(SaleOrder, self).create(vals)

    @api.multi
    def send_dr_conf(self):
        for rec in self:
            
            try:
                #DEFINE THE SERVER
                #server = self.env['res.distributor.database'].search([('database','=',rec.dist_db)], limit=1).distributor_id
                #server.db = rec.dist_db
                #pool = RPCProxy(server)

                #pool.get('purchase.order').write([[rec.dist_po_id],{
                #    'status': "for_dr_conf",
                #}])

                rec.status='for_dr_conf'
            except:
                pass


    @api.multi
    def send_for_delivery_conf(self):
        for rec in self:

            try:
                #DEFINE THE SERVER
                #server = self.env['res.distributor.database'].search([('database','=',rec.dist_db)], limit=1).distributor_id
                #server.db = rec.dist_db
                #pool = RPCProxy(server)

                #pool.get('purchase.order').write([[rec.dist_po_id],{
                #    'status': "for_delivery_conf",
                #}])

                rec.status='for_delivery_conf'
            except:
                pass


    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('submitted', 'Submitted'),
        ('for_dr_conf', 'For DR Confirmation'),
        ('confirmed_dr', 'Confirmed DR'),
        ('for_delivery_conf', 'For Delivery Confirmation'),
        ('confirmed_del', 'Confirmed Delivery'),
        ('enroute', 'Enroute'),
        ('received', 'Received'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    odoo_po_no = fields.Char('ODOO PO Number')

    status = fields.Selection(STATE_SELECTION, 'Status', readonly=True,
                              help="The status of the purchase order or the quotation request. "
                                   "A request for quotation is a purchase order in a 'Draft' status. "
                                   "Then the order has to be confirmed by the user, the status switch "
                                   "to 'Confirmed'. Then the supplier must confirm the order to change "
                                   "the status to 'Approved'. When the purchase order is paid and "
                                   "received, the status becomes 'Done'. If a cancel action occurs in "
                                   "the invoice or in the receipt of goods, the status becomes "
                                   "in exception.",
                              select=True, copy=False, default='draft')

    drf_line_ids = fields.One2many('dmpi.so.drf.line','sale_order_id', "DRF Lines")

    #DRF RECEIVING
    po_ref = fields.Char('PO Reference')
    shipment_no = fields.Char('Shipment No')
    forwarder = fields.Char('Forwarder')
    container = fields.Char('Container')
    plate_no = fields.Char('Plate No')
    gi_date = fields.Date('GI Date')
    received_date = fields.Date('Rec Date')

    seal_no = fields.Char('Seal No')
    drf_no = fields.Char('DRF No')
    invoice_no = fields.Char('Invoice No')

    sold_to = fields.Char('Sold To')
    ship_to = fields.Char('Ship To')

    system_rdd = fields.Date('System RDD')
    shipment_dd = fields.Date('Shipment Date')
    po_approval = fields.Selection([('04','Approved'),('05','Cancelled')],"PO Approval")


    dist_db = fields.Char('Database')
    dist_po_id = fields.Integer('PO ID')




class DmpiSoDrfline(models.Model):
    _name = 'dmpi.so.drf.line'

    product_id = fields.Many2one('product.product', 'Product')
    deliver_quantity = fields.Float('Deliver Quantity')
    actual_quantity = fields.Float('Actual Quantity')
    product_uom = fields.Many2one('product.uom', 'UOM')
    return_reason_id = fields.Many2one('stock.return.reason', 'Return Reason')
    drf_code = fields.Char('DRF Code')
    lot_no = fields.Char('Lot No')
    sale_order_id = fields.Many2one('sale.order', 'Purchase Order')
    variance = fields.Float('Variance')

    sap_so_no = fields.Char('SAP SO No')
    odoo_line_no = fields.Integer("Line No")
    so_line_no = fields.Char('SO Line No')
    dr_no = fields.Char('DR No')
    dr_line_no = fields.Char('DR Line No')

    PO_STATUS2 = [
        ('08', 'Completed'),
        ('09', 'Shortage'),
        ('10', 'Overage w/ SO'),
        ('11', 'Overage w/ Returns')
    ]

    po_status = fields.Selection(PO_STATUS2,'PO Status')


    @api.onchange('actual_quantity')
    def on_change_actual_quantity(self):
        if abs(self.actual_quantity) == abs(self.deliver_quantity):
            self.po_status = '08'
            self.actual_quantity = abs(self.actual_quantity)


        if abs(self.actual_quantity) > abs(self.deliver_quantity):
            self.po_status = '10'
            self.variance =  abs(abs(self.actual_quantity) - abs(self.deliver_quantity))
            self.actual_quantity = abs(self.actual_quantity)

        if abs(self.actual_quantity) < abs(self.deliver_quantity):
            self.po_status = '09'
            self.variance = abs(abs(self.actual_quantity) - abs(self.deliver_quantity))
            self.actual_quantity = abs(self.actual_quantity)

        if self.po_status == '10':
            self.return_reason_id = self.env['stock.return.reason'].search([('code','like','NOBC')], limit=1).id

