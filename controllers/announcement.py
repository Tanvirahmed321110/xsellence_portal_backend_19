from datetime import timedelta
from odoo import fields, http
from odoo.http import request


class XsellenceNoticeBoardController(http.Controller):

    @http.route('/notice-board/data', type='json', auth='user', website=True)
    def notice_board_data(self):
        today = fields.Date.context_today(request.env.user)
        tomorrow = today + timedelta(days=1)

        items = []

        announcements = request.env['hr.announcement'].sudo().search([
            ('active', '=', True),
        ], order='id desc')

        for rec in announcements:
            items.append({
                'icon': '',
                'text': rec.name,
                'type': 'announcement',
            })

        public_holidays = request.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', False),
            ('company_id', 'in', [False, request.env.company.id]),
            ('date_from', '!=', False),
        ])

        for holiday in public_holidays:
            if holiday.date_from and holiday.date_from.date() == tomorrow:
                items.append({
                    'icon': '📅',
                    'text': 'Tomorrow is public holiday: %s' % (holiday.name or 'Holiday'),
                    'type': 'holiday',
                })

        return {'items': items}
