from odoo import fields, models


class XsellenceAssignmentNotification(models.Model):
    _name = 'xsellence.assignment.notification'
    _description = 'Assignment Notification'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', required=True, index=True, ondelete='cascade')
    title = fields.Char(required=True)
    description = fields.Text(required=True)
    view_url = fields.Char(required=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    is_read = fields.Boolean(default=False, index=True)

    def create_for_users(self, user_ids, values):
        # Centralize notification creation so project/task events can reuse the
        # same write path and keep the payload consistent.
        if not user_ids or not values:
            return self.browse()

        notification_values = []
        unique_user_ids = {int(user_id) for user_id in user_ids if user_id}

        for user_id in unique_user_ids:
            notification_values.append({
                'user_id': user_id,
                'title': values['title'],
                'description': values['description'],
                'view_url': values['view_url'],
                'res_model': values['res_model'],
                'res_id': values['res_id'],
            })

        return self.sudo().create(notification_values)
