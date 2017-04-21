from odoo import api, fields, models, _

#Remote IDS

class stock_return_reason(models.Model): #OK
    _inherit = 'stock.return.reason'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['stock.return.reason'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

class product_uom_categ(models.Model): #OK
    _inherit = 'product.uom.categ'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['product.uom.categ'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

class product_uom(models.Model):
    _inherit = 'product.uom' #OK
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['product.uom'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)
    
class product_category(models.Model): #OK
    _inherit = 'product.category'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['product.category'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

class product_template(models.Model): #OK
    _inherit = 'product.template' 
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['product.template'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)
    
class product_product(models.Model): #OK
    _inherit = 'product.product'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['product.product'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

class res_partner_channel(models.Model): #OK
    _inherit = 'res.partner.channel'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['res.partner.channel'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)
    
class res_partner_coverage(models.Model): #OK
    _inherit = 'res.partner.coverage'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['res.partner.coverage'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

class account_tax(models.Model): #OK
    _inherit = 'account.tax'
    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
    def get_default_rid(self):
        rid = self.env['account.tax'].search([], order='rid desc',limit=1).rid or 0
        return rid + 1
    rid = fields.Integer('Remote ID',default=get_default_rid)

#class product_pricelist_type(models.Model):
#    _inherit = 'product.pricelist.type'
#    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
#    rid = fields.Integer('Remote ID')
    
#class product_pricelist(models.Model):
#    _inherit = 'product.pricelist'
#    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
#    rid = fields.Integer('Remote ID')

#class product_pricelist_version(models.Model):
#    _inherit = 'product.pricelist.version'
#    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
#    rid = fields.Integer('Remote ID')
    
#class product_pricelist_item(models.Model):
#    _inherit = 'product.pricelist.item'
#    _sql_constraints = [('rid', 'unique(rid)', 'Please enter Unique ID'),]
#    rid = fields.Integer('Remote ID')
