from datetime import timedelta

from odoo import fields, http
from odoo.http import request


class XsellencePortalNotifications(http.Controller):

    @http.route('/assignment/notifications', type='jsonrpc', auth='user', website=True)
    def assignment_notifications(self, **kw):
        # Keep only the latest one month of notifications in the sidebar/popup feed.
        last_month_date = fields.Datetime.now() - timedelta(days=30)

        notifications = request.env['xsellence.assignment.notification'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('create_date', '>=', fields.Datetime.to_string(last_month_date)),
        ], order='is_read asc, create_date desc')

        unread_notifications = notifications.filtered(lambda rec: not rec.is_read)

        # Return a richer payload so the existing popup and the new sidebar can
        # both use the same backend endpoint without any HTML design changes.
        return {
            'count': len(notifications),
            'unread_count': len(unread_notifications),
            'notifications': [{
                'id': notification.id,
                'title': notification.title,
                'desc': notification.description,
                'view_url': notification.view_url,
                'is_read': notification.is_read,
                'res_model': notification.res_model,
                'res_id': notification.res_id,
                'create_date': notification.create_date.isoformat() if notification.create_date else False,
            } for notification in notifications],
        }

    @http.route('/assignment/notifications/read', type='jsonrpc', auth='user', website=True)
    def assignment_notification_read(self, notification_id=None, **kw):
        # Mark the clicked notification as read so the badge and the ::after
        # indicator disappear immediately on the next render.
        if notification_id:
            notification = request.env['xsellence.assignment.notification'].sudo().search([
                ('id', '=', int(notification_id)),
                ('user_id', '=', request.env.user.id),
            ], limit=1)

            if notification:
                notification.write({'is_read': True})

        return {'success': True}
