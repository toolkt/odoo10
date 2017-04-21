import logging
import werkzeug

from odoo import http,models,fields, _
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'


    sub_login = fields.Char('Sub Login')
    ug = fields.Selection([('a','A'),('b','B'),('c','C')])


class AuthSignupHome(Home):

    @http.route()
    def web_login(self, *args, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return http.redirect_with_hash(request.params.get('redirect'))

        usergroups = []
        u = request.env['res.users'].sudo().search([])
        for rec in u:
            print rec.login
            usergroups.append(rec.login)

        print dict(request.params)

        request.params['login'] = 'admin'
        #request.params['password'] = 'admin'
        request.params['user_group'] = 'admin'
        request.ug = ''

        response = super(AuthSignupHome, self).web_login(*args, **kw)
        if response.is_qweb:

            response.qcontext['usergroups'] = usergroups
            


        return response



