from odoo import http
from odoo.http import request
from werkzeug.utils import redirect
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging

_logger = logging.getLogger(__name__)


class CustomerPortalInherit(CustomerPortal):

   @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
   def home(self, **kw):
       user = request.env.user
       if user.has_group('base.group_system'):  # Administrator
           return redirect('/web')

       elif user.has_group('base.group_user'):  # Internal User
           return redirect('/web')

       elif user.has_group('base.group_portal'):  # Portal User
           return redirect('/dashboard')

       else:
           return redirect('/dashboard')