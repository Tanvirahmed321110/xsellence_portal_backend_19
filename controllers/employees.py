from odoo import http
from odoo.http import request


class XsellencePortal(http.Controller):

    # ========================
    # For All Employees
    # ========================
    @http.route('/employees', type='http', auth='user', website=True)
    def dashboard_f(self, **kw):
        Employees = request.env['hr.employee'].sudo()
        employees = Employees.search([('active', '=', True),])
        total = Employees.sudo().search_count([('active', '=', True),])


        return request.render('xsellence_portal.employees_page', {
            'active_menu': 'employees',
            'employees':employees,
            'total':total,

            'breadcrumb': [
                {'name': 'Dashboard', 'url': '/dashboard'},
                {'name': 'Employees', 'url': False},
            ]
        })