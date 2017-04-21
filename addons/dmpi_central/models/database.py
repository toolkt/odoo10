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

from fabric.api import *
import paramiko
import socket
import os
import glob


ODOO_MODULES_DIR = '/tmp/modules/'

@parallel
def restart_server():
    with settings(warn_only=True):
        print "RESTART SERVER"
        sudo("pkill -f odoo", pty=False)
        sudo("service odoo-server restart", pty=False)


#@parallel
def update_modules(database,modules):
    with settings(warn_only=True):
        print "RESTART SERVER"
        sc = 'su -c "setsid /opt/odoo/server/openerp-server -c /etc/odoo-server.conf -u %s -d %s  >/dev/null 2>&1 < /dev/null &" -s /bin/sh odoo' % (modules,database)
        print sc
        sudo("pkill -f odoo")
        sudo(sc)
        #sudo("service odoo-server restart", pty=False)


#@parallel
def install_modules(database,modules):
    with settings(warn_only=True):
        print "RESTART SERVER"
        sc = 'su -c "setsid /opt/odoo/server/openerp-server -c /etc/odoo-server.conf -i %s -d %s  >/dev/null 2>&1 < /dev/null &" -s /bin/sh odoo' % (modules,database)
        print sc
        sudo("pkill -f odoo")
        sudo(sc)
        #sudo("service odoo-server restart", pty=False)



#@parallel
def file_send(localpath,remotepath):
    with settings(warn_only=True):
        put(localpath,remotepath,use_sudo=True)

#@parallel
def file_extract(remotepath):
    with settings(warn_only=True):
        with cd(remotepath):
            sudo("dpkg -s unzip 2>/dev/null >/dev/null || sudo apt-get -y install unzip")
            sudo("unzip -o \*.zip")
            sudo("rm *.zip")
            sudo("chmod 777 -R *")

class PGConn(object):
    def __init__(self, server):
        self.server = server
        self.conn_string = "host=%s dbname=%s user=%s password=%s" % (server.remote_host, server.database, 
                                                                server.postgres_user,server.postgres_pass)

    def execute(self, resource):
        self.conn = psycopg2.connect(self.conn_string)
        self.cursor = self.conn.cursor()
        self.cursor.execute(resource)
        self.conn.commit() 
        return self.cursor

def is_date(string):
    try: 
        parse(string)
        return True
    except ValueError:
        return False


def create_multi_upsert_query(table,columns,add_columns,remove_column,values,subquery,mode,missing=''):
    #http://stackoverflow.com/questions/1109061/insert-on-duplicate-update-in-postgresql/8702291#8702291
    #values = ','.join(values)
    vals = []
    unique_ids = []
    for v in values:
        row = ""
        c = 0
        for i in v:
            #print "----",i
            rowstr=""
            if isinstance(i, (numbers.Number,decimal.Decimal)):
                rowstr = "%s"%i
                #print "--Number"
            elif isinstance(i, (datetime)):
                rowstr = "'%s'::DATE"%i
                #print "--Date"
            else:
                if i == None:
                    rowstr = "Null"
                else:
                    rowstr = "'%s'"%i.replace("'","''")

                try: 
                    datetime.strptime(i, '%Y-%m-%d')
                    rowstr = "'%s'::DATE"%i
                except:
                    pass


            if c<1:
                rowstr = "%s"%rowstr
            else:
                rowstr = ",%s"%rowstr
            row = "%s%s"%(row,rowstr)
            c += 1

        vals.append('(%s)' % row)

        unique_ids.append(v[0])


    f = []
    counter = 0
    id_field = ''

    query_col = ','.join(['"%s"'%str(i) for i in columns])
    
    if add_columns:
        for c in add_columns:
            columns.append(c)

    if remove_column:
        for c in remove_column:
            columns.remove(c)

    for i in columns:
        if counter < 1:
            id_field = i
        else:
            f.append("%s = nv.%s" % (i,i,))
        counter += 1
    add_col=""

    columns = ','.join(['"%s"'%str(i) for i in columns])


    values = ',\n'.join(vals)
    fields = ',\n'.join(f)
    squery = "select * from nval"

    if subquery:
        squery = subquery

    query = ""
    if mode == 'upsert':
        query = """WITH nval (%s) as (
                    values 
                        %s 
                    ),
                    new_values as (
                    %s
                    ),
                    upsert as
                    ( 
                        update %s m 
                            set 
                                %s
                        FROM new_values nv
                        WHERE m.%s = nv.%s
                        RETURNING m.*
                    )
                    INSERT INTO %s (%s)
                    SELECT %s
                    FROM new_values
                    WHERE NOT EXISTS (SELECT 1 
                                      FROM upsert up 
                                      WHERE up.%s = new_values.%s)

        """ % (query_col,values,squery,table,fields,id_field,id_field,table,columns,columns,id_field,id_field)

    if mode == 'insert':
        query = """WITH nval (%s) as (
                    values 
                        %s 
                    ),
                    new_values as (
                    %s
                    )
                    INSERT INTO %s (%s)
                    SELECT %s
                    FROM new_values

        """ % (query_col,values,squery,table,columns,columns)


    queries = []
    queries.append(query)

    if missing == 'deactivate':
        #print unique_ids
        ids = ','.join([ str(i) for i in unique_ids])

        deactivate_query = """ UPDATE %s set active=False where id not in (%s);
        """ % (table,str(ids))

        queries.append(deactivate_query)

    if missing == 'delete':
        #print unique_ids
        ids = ','.join([ str(i) for i in unique_ids])
        deactivate_query = """ DELETE FROM %s where id not in (%s);
        """ % (table,str(ids))
        queries.append(deactivate_query)
        
    return queries





class ResDistributorDatabase(models.Model):
    _name = "res.distributor.database"

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner','Partner')

    remote_host = fields.Char('Host')
    remote_port = fields.Integer('Port', default=8069)
    xmlrpc_user = fields.Char('RPC User')
    xmlrpc_pass = fields.Char('RPC Password')
    postgres_user = fields.Char('PG User')
    postgres_pass = fields.Char('PG Password')
    ssh_user = fields.Char('SSH User')
    ssh_pass = fields.Char('SSH Password')


    database = fields.Char('Database')
    #distributor_id = fields.Many2one('res.distributor','Distributor')
    dist_channel = fields.Selection([('20','GT'),('30','MT')],'Distributor Channel')

    live = fields.Boolean('Live')
    show_error = fields.Boolean('Show Error')
    active = fields.Boolean('Active', default=True)
    allocation_ids = fields.One2many('dmpi.dist.po.allocation','database_id',"Allocation")


    cutoff_start = fields.Date('Start')
    cutoff_end = fields.Date('End')
    cutoff = fields.Boolean('Cutoff')
    cutoff_msg = fields.Char('Cutoff Message')

    upload_sales_enable = fields.Boolean("Upload Sales", default=1)
    upload_returns_enable = fields.Boolean("Upload Returns", default=1)
    upload_partner_enable = fields.Boolean("Upload Partner", default=1)
    upload_partner_reclass_enable = fields.Boolean("Upload Partner Reclass", default=1)

    bypass_load_limit = fields.Boolean("Bypass Inland Load Limit", default=1)
    bypass_load_limit_off_shore = fields.Boolean("Bypass Off Shore Load Limit", default=1)
    inland_sdd = fields.Integer('Inland SDD')
    offshore_sdd = fields.Integer('Offshore SDD')

    max_truck_load_weight_kg = fields.Float(string='10w Load (kg)')
    max_van_load_weight_kg = fields.Float(string='CV Load (kg)')

    max_truck_load = fields.Float(string='MAX Truck Load (%)')
    min_truck_load = fields.Float(string='MIN Truck Load (%)')

    max_truck_load_weight = fields.Float(string='MAX Truck Load Weight (%)')
    min_truck_load_weight = fields.Float(string='MIN Truck Load Weight (%)')

    central_host = fields.Char('Central Host')
    central_port = fields.Integer('Central Port', default=8069)
    central_user = fields.Char('Central User')
    central_pass = fields.Char('Central Password')
    central_db = fields.Char('Central DB')
    distributor_db = fields.Char('Distributor DB')

    distributor_root_password = fields.Char('Root Password')
    module_ids = fields.Many2many('res.distributor.database.module', 'res_distributor_database_module_rel', 'database_id','module_id', string='Modules')
    module_dir = fields.Char('Modules Directory')

    log_ids = fields.One2many('res.distributor.database.log','database_id',"Database Logs")
    schedule_ids = fields.One2many('res.distributor.database.schedule','database_id',"Database Schedule")
    log_date = fields.Datetime('Log Date')
    log_status = fields.Selection([(1,'Success'),(0,'Failed')],'Log Status')


    @api.multi
    def sync_company_settings(self):
        for rec in self:
            if rec.live: 
                #DEFINE THE SERVER
                #print 

                odoo = odoorpc.ODOO(rec.remote_host, port=rec.remote_port)
                odoo.login(rec.database, rec.xmlrpc_user, rec.xmlrpc_pass)

                cids = odoo.env['res.company'].search([])
                print "------------B------------------"

                for cid in cids:
                    company_obj = odoo.env['res.company']
                    company = company_obj.browse(cid)

                    company.write({
                        'cutoff_start' : rec.cutoff_start,
                        'cutoff_end' : rec.cutoff_end,
                        'cutoff' : rec.cutoff,
                        'cutoff_msg' : rec.cutoff_msg,
                        'upload_sales_enable' : rec.upload_sales_enable,
                        'upload_returns_enable' : rec.upload_returns_enable,
                        'upload_partner_enable' : rec.upload_partner_enable,
                        'upload_partner_reclass_enable' : rec.upload_partner_reclass_enable,
                        'sold_to_code' : rec.partner_id.sold_to_code,
                        'inland_sdd' : rec.inland_sdd,
                        'offshore_sdd' : rec.offshore_sdd,

                        'bypass_load_limit' : rec.bypass_load_limit,
                        'bypass_load_limit_off_shore' : rec.bypass_load_limit_off_shore,
                        'inland_sdd' : rec.inland_sdd,
                        'offshore_sdd' : rec.offshore_sdd,
                        'max_truck_load_weight_kg' : rec.max_truck_load_weight_kg,
                        'max_van_load_weight_kg' : rec.max_van_load_weight_kg,

                        'max_truck_load_weight' : rec.max_truck_load_weight,
                        'min_truck_load_weight' : rec.min_truck_load_weight,

                        'max_truck_load' : rec.max_truck_load,
                        'min_truck_load' : rec.min_truck_load,

                        'central_host' : rec.central_host,
                        'central_port' : rec.central_port,
                        'central_db' : rec.central_db,
                        'distributor_db' : rec.distributor_db,
                        'central_user' : rec.central_user,
                        'central_pass' : rec.central_pass,
                        'dist_channel' : rec.dist_channel,
                    })


    @api.multi
    def apply_to_all_po(self):
        for rec in self:
            db_obj = self.search([('id','!=',rec.id)])
            for db in db_obj:
                db.write({
                    'bypass_load_limit' : rec.bypass_load_limit,
                    'bypass_load_limit_off_shore' : rec.bypass_load_limit_off_shore,
                    'inland_sdd' : rec.inland_sdd,
                    'offshore_sdd' : rec.offshore_sdd,
                    'apply_to_all_po' : rec.apply_to_all_po,
                    })


    @api.multi
    def apply_to_all_wc(self):
        
        for rec in self:
            db_obj = self.search([('id','!=',rec.id)])
            for db in db_obj:
                db.write({
                    'max_truck_load_weight_kg' : rec.max_truck_load_weight_kg,
                    'max_van_load_weight_kg' : rec.max_van_load_weight_kg,
                    })

    @api.multi
    def apply_to_all_vc(self):
        
        for rec in self:
            db_obj = self.search([('id','!=',rec.id)])
            for db in db_obj:
                db.write({
                    'max_truck_load' : rec.max_truck_load,
                    'min_truck_load' : rec.min_truck_load,
                    })


    @api.multi
    def apply_to_all_lc(self):
        
        for rec in self:
            db_obj = self.search([('id','!=',rec.id)])
            for db in db_obj:
                db.write({
                    'max_truck_load_weight' : rec.max_truck_load_weight,
                    'min_truck_load_weight' : rec.min_truck_load_weight,
                    })

    @api.multi
    def apply_to_all_po_automation(self):
        
        for rec in self:
            db_obj = self.search([('id','!=',rec.id)])
            for db in db_obj:
                db.write({
                    'central_host' : rec.central_host,
                    'central_port' : rec.central_port,
                    'central_db' : rec.central_db,
                    })                



    @api.multi
    def change_distributor_root_password(self):
        for rec in self:
            
            log_error = 0
            log_message = []
            modules = []
            try:
                server = rec
                cursor = PGConn(server)
                query = "UPDATE res_users set password='%s' where login = 'admin'" % rec.distributor_root_password
                cursor.execute(query)

                msg = 'SUCCESSFULY Updated the Admin Password'
                log_message.append(msg)                      
            except:
                msg = 'FAILED Updating the Admin Password'
                log_message.append(msg)  
                log_error += 1

            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'UPDATE PASSWORD')



    @api.multi
    def clear_pricelist(self):
        for rec in self:
            server = rec
            cursor = PGConn(server)     

            log_error = 0
            log_message = []


            try:
                query = """DELETE from product_pricelist_item where (product_id > 0) or (product_tmpl_id > 0)"""
                cursor.execute(query) 

                msg = 'SUCCESSFULY Updated Table: product_pricelist_item'
                log_message.append(msg)                
            except:
                msg = 'FAILED Updating Table: product_pricelist_item'
                log_message.append(msg)  
                log_error += 1
                pass


            try:
                query = """DELETE FROM product_pricelist_version WHERE id in (
                SELECT V.ID from product_pricelist_version v
                left join product_pricelist p on p.id = v.pricelist_id
                where p."name" in ('Public Pricelist','Default Purchase Pricelist') and 
                v.name not like 'Default%')"""
                cursor.execute(query) 

                msg = 'SUCCESSFULY Updated Table: product_pricelist_version'
                log_message.append(msg)                
            except:
                msg = 'FAILED Updating Table: product_pricelist_version'
                log_message.append(msg)  
                log_error += 1
                pass

            try:
                query = """SELECT setval('product_pricelist_version_id_seq', COALESCE((SELECT MAX(id)+1 
                    FROM product_pricelist_version), 1), false)
                    """
                cursor.execute(query) 

                msg = 'SUCCESSFULY Updated Resetting Table: product_pricelist_version'
                log_message.append(msg)                
            except:
                msg = 'FAILED Updating Table: product_pricelist_version'
                log_message.append(msg)  
                log_error += 1
                pass


            try:
                query = """SELECT setval('product_pricelist_id_seq', COALESCE((SELECT MAX(id)+1 
                    FROM product_pricelist), 1), false)
                    """
                cursor.execute(query) 
                msg = 'SUCCESSFULY Updated Resetting Table: product_pricelist'
                log_message.append(msg)                
            except:
                msg = 'FAILED Updating Resetting Table: product_pricelist'
                log_message.append(msg)  
                log_error += 1
                pass


            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'FIX PRICELIST')



    @api.multi
    def sync_data(self):
        for rec in self:
            if rec.live: 

                queries = []
                log_message = []
                log_error = 0
                #Sync res_partner_coverage
                query = """SELECT 
                            rid as id, name, van_sale, active from res_partner_coverage
                            order by rid
                            """

                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'res_partner_coverage'
                res_partner_coverage_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print res_partner_coverage_query
                for q in res_partner_coverage_query:
                    load = {'table':table,'query':q}
                    queries.append(load)                

                #Sync res_partner_channel
                query = """SELECT 
                            rp.rid as id,rp.name,rp.channel_type,rp.code,parent.rid as parent_id,rp.active
                            FROM res_partner_channel rp
                            left join res_partner_channel parent on parent.id = rp.parent_id
                            order by rp.rid
                            """


                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'res_partner_channel'
                res_partner_channel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print res_partner_channel_query
                for q in res_partner_channel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync stock_return_reason
                query = """SELECT rid as id,code,name,return_type from stock_return_reason
                            order by rid
                            """


                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'stock_return_reason'
                stock_return_reason_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print stock_return_reason_query
                for q in stock_return_reason_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync product_uom_categ
                query = """SELECT 
                            id,name from product_uom_categ
                            order by id
                            """

                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_uom_categ'
                product_uom_categ_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_uom_categ_query
                for q in product_uom_categ_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync product_category
                query = """SELECT pc.rid as id,pid.rid as parent_id, pl.rid as parent_left,pr.rid as parent_right,
                            pc.name,pc.type
                            from product_category pc
                            left join product_category pid on pid.id = pc.parent_id
                            left join product_category pl on pl.id = pc.parent_left
                            left join product_category pr on pr.id = pc.parent_right
                            order by pc.rid
                            """
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_category'
                product_category_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_category_query
                for q in product_category_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   



                #Sync account_tax
                query = """SELECT rid as id, sequence, include_base_amount,description,
                            type_tax_use,active,name,amount,price_include
                            from account_tax
                            order by rid
                            """
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'account_tax'
                account_tax_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print account_tax_query
                for q in account_tax_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   



                #Sync product_template
                query = """SELECT rid as id,name,rounding,active,factor,uom_type,category_id 
                        from product_uom order by rid
                        """
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_uom'
                product_uom_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_uom_query
                for q in product_uom_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync product_template
                query = """ SELECT pt.rid as id,uom.rid as uom_id,uom.rid as uos_id, uom.rid as uom_po_id,categ.rid as categ_id,
                    pt.list_price, pt.weight, pt.sale_ok, pt.purchase_ok, 1 as company_id, 1 as uos_coeff,
                    pt.description_sale,pt.description,pt.volume,pt.active,pt.name,pt.type,
                    pt.sale_delay
                    from product_template pt
                    left join product_uom as uom on uom.id = pt.uom_id
                    left join product_category categ on categ.id = pt.categ_id
                    """
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_template'
                product_template_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert','deactivate') 
                #print product_template_query
                for q in product_template_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync product_product
                query = """SELECT pp.rid as id,pp.default_code,pt.name as name_template,pt.rid as product_tmpl_id,pp.active
                    from product_product pp 
                    left join product_template pt on pt.id = pp.product_tmpl_id
                    """
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_product'
                product_product_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert','deactivate') 
                #print product_product_query
                for q in product_product_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   

                

                #Sync product_taxes_rel
                query = """SELECT p.rid as prod_id, tax.rid as tax_id 
                    from product_taxes_rel pt
                    left join account_tax tax on tax.id = pt.tax_id
                    left join product_template p on p.id = pt.prod_id
                    """
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_taxes_rel'
                product_taxes_rel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_product_query
                for q in product_taxes_rel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   
              


                #Sync product_taxes_rel
                query = """SELECT p.rid as prod_id, tax.rid as tax_id 
                    from product_supplier_taxes_rel pt
                    left join account_tax tax on tax.id = pt.tax_id
                    left join product_template p on p.id = pt.prod_id
                    """
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'product_supplier_taxes_rel'
                product_supplier_taxes_rel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_product_query
                for q in product_supplier_taxes_rel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   



                #Sync ir_property
                query = """SELECT 'product.template,'||pt.rid as res_id,irp.value_float, irp.name, irp.type, irp.company_id
                        FROM(
                            SELECT split_part(ip.res_id, ',', 2)::INTEGER as product_id,
                            ip.value_text,ip.value_float,ip.name,ip.type,1 as company_id
                            from ir_property ip
                            where name = 'standard_price'
                            ) as irp
                        left join product_product pp on pp.id = irp.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id"""
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]
                #remove_column = ['res_id','model','res_id_model_id']
                add_columns = ['fields_id']
                subquery = """SELECT nval.*, mf.id as fields_id from nval 
                    left join ir_model_fields mf on mf.name = nval.name and mf.model = 'product.template'
                    """

                table = 'ir_property'
                ir_property_query = create_multi_upsert_query(table,columns,add_columns,False,values,subquery,'upsert') 
                for q in ir_property_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Reset IDs of pricelist pkey
                product_pricelist_reset_id = """SELECT setval('product_pricelist_id_seq', COALESCE((SELECT MAX(id)+1 
                    FROM product_pricelist), 1), false)
                    """
                load = {'table':'product_pricelist','query':product_pricelist_reset_id}
                #print product_pricelist_reset_id
                queries.append(load) 

                #Sync product_pricelist_version
                query = """SELECT CASE
                        WHEN type = 'sale' THEN name||' (S)'
                        WHEN type = 'purchase' THEN name||' (P)'
                        END as name,
                        date_start,date_end,type,active from dmpi_product_pricelist where active = True"""
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                if values:
                    columns = [column[0] for column in self._cr.description]
                    remove_column = ['type']
                    add_columns = ['pricelist_id']
                    subquery = """SELECT nval.*, 
                        CASE WHEN nval.type = 'sale' THEN 
                            (SELECT id as pricelist_id from product_pricelist where name = 'Public Pricelist')
                            WHEN nval.type = 'purchase' THEN 
                            (SELECT id as pricelist_id from product_pricelist where name = 'Default Purchase Pricelist')
                        END as pricelist_id from nval  
                         """

                    table = 'product_pricelist_version'
                    product_pricelist_version_query = create_multi_upsert_query(table,columns,add_columns,remove_column,values,subquery,'upsert') 
                    #print product_pricelist_query[0]
                    
                    for q in product_pricelist_version_query:
                        #print q
                        load = {'table':table,'query':q}
                        queries.append(load)   


                #Reset IDs of pricelist items      
                product_pricelist_item_reset_id = """SELECT setval('product_pricelist_item_id_seq', COALESCE((SELECT MAX(id)+1 
                    FROM product_pricelist_item), 1), false)
                    """
                load = {'table':'product_pricelist_item','query':product_pricelist_item_reset_id}
                #print product_pricelist_item_reset_id
                queries.append(load)      


                #Sync product_pricelist_item
                query = """SELECT  CASE
                        WHEN p.type = 'sale' and i.default = FALSE THEN pp.default_code ||' S('||p.name||')'
                        WHEN p.type = 'purchase' and i.default = FALSE THEN pp.default_code ||' P('||p.name||')'
                        WHEN p.type = 'sale' and i.default = TRUE THEN 'DEFAULT S('||p.name||')'
                        WHEN p.type = 'purchase' and i.default = TRUE THEN 'DEFAULT P('||p.name||')'
                        END as name,

                        0.0 as price_round,

                        CASE
                        WHEN p.type = 'sale' and i.default = FALSE THEN -1.0
                        WHEN p.type = 'purchase' and i.default = FALSE THEN -1.0
                        WHEN p.type = 'sale' and i.default = TRUE THEN 0.0
                        WHEN p.type = 'purchase' and i.default = TRUE THEN 0.0
                        END as price_discount,

                        CASE
                        WHEN p.type = 'sale' THEN 1
                        WHEN p.type = 'purchase' THEN 2
                        END as base,

                        i.sequence,i.unit_price as price_surcharge, i.unit_price as fixed_price, 

                        NOT(i.default) as is_fixed_price,

                        0 as min_quantity,
                        CASE
                        WHEN p.type = 'sale' THEN p.name||' (S)'
                        WHEN p.type = 'purchase' THEN p.name||' (P)'
                        END as pricelist_name,
                        pp.default_code,p.type
                        from dmpi_product_pricelist_item i
                        left join product_product pp on pp.id = i.product_id
                        left join dmpi_product_pricelist p on p.id = i.pricelist_id"""
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                if values:
                    columns = [column[0] for column in self._cr.description]
                    remove_column = ['pricelist_name','default_code','type']
                    add_columns = ['price_version_id','product_id']
                    subquery = """SELECT nval.*, ppv.id as price_version_id, pp.id as product_id
                                from nval 
                                left join product_pricelist_version as ppv on ppv.name = nval.pricelist_name
                                left join product_product pp on (pp.default_code = nval.default_code) and (pp.active = TRUE)
                                """

                    table = 'product_pricelist_item'
                    product_pricelist_item_query = create_multi_upsert_query(table,columns,add_columns,remove_column,values,subquery,'upsert') 
                    #print product_pricelist_item_query
                    for q in product_pricelist_item_query:
                        print q
                        load = {'table':table,'query':q}
                        queries.append(load)  


                #Sync Deliver To
                query = """SELECT rp.id,rp.name,rp.ship_to_code as code
                        from res_partner rp
                        where type = 'delivery' and parent_id = %s
                     """ % rec.partner_id.id
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'dmpi_ship_to'
                ship_to_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_pricelist_version_query
                for q in ship_to_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   



                #Sync dmpi plant
                query = """SELECT id,name,description from dmpi_plant """
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'dmpi_plant'
                product_supplier_taxes_rel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_product_query
                for q in product_supplier_taxes_rel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync dmpi_dist_po_allocation
                query = """SELECT id,name,date_start,date_end,active from dmpi_dist_po_allocation where database_id = %s """ % rec.id
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'dmpi_dist_po_allocation'
                product_supplier_taxes_rel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_product_query
                for q in product_supplier_taxes_rel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                #Sync dmpi_dist_po_allocation_line
                query = """SELECT l.id,l.deliver_source,pp.rid as product_id,l.allocation_id,l.plant_id,l.allocation,
                        pt.cases_pa,pt.cases_cv,pt.cases_tw,pt.weight,a.date_start,a.date_end,pt.name,l.critical
                        from dmpi_dist_po_allocation_line l
                        left join dmpi_dist_po_allocation a on a.id = l.allocation_id
                        left join product_product pp on pp.id = l.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id
                        where a.database_id = %s""" % rec.id
                            
                self._cr.execute(query)
                values = self._cr.fetchall()
                columns = [column[0] for column in self._cr.description]

                table = 'dmpi_dist_po_allocation_line'
                product_supplier_taxes_rel_query = create_multi_upsert_query(table,columns,False,False,values,False,'upsert') 
                #print product_product_query
                for q in product_supplier_taxes_rel_query:
                    load = {'table':table,'query':q}
                    queries.append(load)   


                server = rec
                cursor = PGConn(server)

                for query in queries:
                    print "---------"
                    #print query
                    
                    try:
                        cursor.execute(query['query'],) 
                        msg = 'SUCCESSFULY Updated Table: %s' % query['table']
                        log_message.append(msg)
                    except:
                        msg = 'FALIED Updating Table: %s' % query['table']
                        log_message.append(msg)
                        log_error += 1
                        if rec.show_error:
                            raise UserError('ERROR executing query for: %s \n\n %s' % (query['table'],query['query']))
                        else:
                            pass


            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'SYNC DATA')



    @api.one
    def log_result(self,log_error,message,name):

        log_date = datetime.now()
        
        print message
        log_status = 1
        if log_error > 0:
            log_status = 0

        self.log_date = log_date
        self.log_status = log_status


        self.log_ids.create({
                'name':name,
                'log_date':log_date,
                'log_note': message,
                'log_status': log_status,
                'database_id':self.id,
            })        


    @api.multi
    def restart_distributor_server(self):
        for rec in self:
            log_error = 0
            log_message = []
            try:
                #ESTABLISH FABRIC
                host_string = rec.ssh_user + '@' + rec.remote_host + ':22'
                env.hosts.append(host_string)
                env.passwords[host_string] = rec.ssh_pass

                execute(restart_server)
                msg = 'SUCCESSFULY Restarted the Server'
                log_message.append(msg)                
            except:
                msg = 'FAILED Restartng the Server'
                log_message.append(msg)  
                log_error += 1
                pass


            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'RESTART SERVER')

    @api.multi
    def upload_module(self):
        for rec in self:
            log_error = 0
            log_message = []
            modules = []
            #ESTABLISH FABRIC
            try:
                host_string = rec.ssh_user + '@' + rec.remote_host + ':22'
                env.hosts.append(host_string)
                env.passwords[host_string] = rec.ssh_pass

                directory = ODOO_MODULES_DIR

                for m in rec.module_ids:
                    localpath = '%s%s.zip' % (directory,m.name)
                    print localpath
                    remotepath = '%s/%s.zip' % (rec.module_dir,m.name)
                    print remotepath
                    execute(file_send,localpath,remotepath)
                    modules.append(m.name)
                execute(file_extract,rec.module_dir)

                msg = 'SUCCESSFULY Uploaded the Modules: %s' % ','.join([m for m in modules])
                log_message.append(msg)                      
            except:
                msg = 'FAILED Uploading the Modules: %s' % ','.join([m for m in modules])
                log_message.append(msg)  
                log_error += 1

            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'UPLOAD MODULES')




    @api.multi
    def upgrade_module(self):
        for rec in self:


            log_error = 0
            log_message = []
            modules = []
            try:
                #ESTABLISH FABRIC
                host_string = rec.ssh_user + '@' + rec.remote_host + ':22'
                env.hosts.append(host_string)
                env.passwords[host_string] = rec.ssh_pass

                modules = ','.join([m.name for m in rec.module_ids])
                database = rec.database
                execute(update_modules,database,modules)

                msg = 'SUCCESSFULY Upgraded the Modules: %s' % modules
                log_message.append(msg)                      
            except:
                msg = 'FAILED Upgrading the Modules: %s' % modules
                log_message.append(msg)  
                log_error += 1

            message = '\n'.join([m for m in log_message])
            rec.log_result(log_error,message,'UPGRADE MODULES')




#    @api.multi
#    def install_module(self):
#        for rec in self:
#            #ESTABLISH FABRIC
#            host_string = rec.ssh_user + '@' + rec.remote_host + ':22'
#            env.hosts.append(host_string)
#            env.passwords[host_string] = rec.ssh_pass

#            modules = ','.join([m.name for m in rec.module_ids])
#            database = rec.database
#            execute(install_modules,database,modules)


            

class ResDistributorDatabaseLog(models.Model):
    _name = "res.distributor.database.log"
    _order = 'log_date desc'

    name = fields.Char('Name')
    log_date = fields.Datetime('Date')
    log_note = fields.Text('Note')
    log_status = fields.Selection([(1,'Success'),(0,'Failed')],'Log Status')
    database_id = fields.Many2one('res.distributor.database',"Database")


class ResDistributorDatabaseSchedule(models.Model):
    _name = "res.distributor.database.schedule"
    _order = 'schedule_date desc'

    name = fields.Char('Function')
    schedule_date = fields.Datetime('Date')
    schedule_status = fields.Selection([(1,'Success'),(0,'Failed')],'Log Status')
    database_id = fields.Many2one('res.distributor.database',"Database")

