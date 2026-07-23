from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'
    _order = 'create_date desc'

    custom_priority = fields.Selection([
        ('normal','normal'),
        ('medium','medium'),
        ('high','high'),
        ('urgent','urgent'),
    ], string=' Priority',default='normal', tracking=True)

    custom_status = fields.Selection([
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Project Status', default='planning', tracking=True)

    # assign members
    assigned_user_ids = fields.Many2many(
        'res.users',
        string='Assigned Users',
        tracking=True
    )

    description = fields.Html(
        string='Description',
        tracking=True,
    )

    def _create_assignment_notifications(self, user_ids):
        Notification = self.env['xsellence.assignment.notification']

        for task in self:
            Notification.create_for_users(user_ids, {
                'title': 'Task Assigned',
                'description': 'You have been added to %s task.' % task.name,
                'view_url': '/tasks/task_details/%s' % task.id,
                'res_model': 'project.task',
                'res_id': task.id,
            })

    def _create_status_change_notifications(self, user_ids):
        Notification = self.env['xsellence.assignment.notification']
        status_labels = dict(self._fields['custom_status'].selection)

        for task in self:
            status_label = status_labels.get(task.custom_status, task.custom_status)
            # Keep task status-change notifications in the same stream so
            # sidebar ordering and unread logic stay consistent.
            Notification.create_for_users(user_ids, {
                'title': 'Task Status Changed',
                'description': '%s task status changed to %s.' % (task.name, status_label),
                'view_url': '/tasks/task_details/%s' % task.id,
                'res_model': 'project.task',
                'res_id': task.id,
            })

    def _create_member_change_notifications(self, added_user_ids=None, removed_user_ids=None):
        Notification = self.env['xsellence.assignment.notification']
        actor_name = self.env.user.name or 'A user'

        for task in self:
            if added_user_ids:
                Notification.create_for_users(added_user_ids, {
                    'title': 'Task Member Added',
                    'description': '%s added you to %s task.' % (actor_name, task.name),
                    'view_url': '/tasks/task_details/%s' % task.id,
                    'res_model': 'project.task',
                    'res_id': task.id,
                })

            if removed_user_ids:
                Notification.create_for_users(removed_user_ids, {
                    'title': 'Task Member Removed',
                    'description': '%s removed you from %s task.' % (actor_name, task.name),
                    'view_url': '/tasks/task_details/%s' % task.id,
                    'res_model': 'project.task',
                    'res_id': task.id,
                })

    def _create_comment_notifications(self, comment_author_name, comment_text):
        Notification = self.env['xsellence.assignment.notification']

        for task in self:
            recipient_ids = set(task.user_ids.ids + task.assigned_user_ids.ids)
            if self.env.user.id:
                recipient_ids.discard(self.env.user.id)

            if not recipient_ids:
                continue

            comment_preview = (comment_text or '').strip().replace('\n', ' ')
            if len(comment_preview) > 120:
                comment_preview = comment_preview[:117] + '...'

            Notification.create_for_users(recipient_ids, {
                'title': 'Task Comment Added',
                'description': '%s commented on %s task: %s' % (comment_author_name, task.name, comment_preview),
                'view_url': '/tasks/task_details/%s' % task.id,
                'res_model': 'project.task',
                'res_id': task.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)

        for task in tasks:
            assigned_user_ids = set(task.user_ids.ids + task.assigned_user_ids.ids)

            if assigned_user_ids:
                task._create_assignment_notifications(assigned_user_ids)

        return tasks

    def write(self, vals):
        old_user_map = {
            task.id: set(task.user_ids.ids + task.assigned_user_ids.ids)
            for task in self
        }
        old_status_map = {
            task.id: task.custom_status
            for task in self
        }

        result = super().write(vals)

        if 'user_ids' in vals or 'assigned_user_ids' in vals:
            for task in self:
                new_user_ids = set(task.user_ids.ids + task.assigned_user_ids.ids)
                added_user_ids = new_user_ids - old_user_map.get(task.id, set())
                removed_user_ids = old_user_map.get(task.id, set()) - new_user_ids

                if added_user_ids:
                    task._create_assignment_notifications(added_user_ids)
                    task._create_member_change_notifications(added_user_ids=added_user_ids)

                if removed_user_ids:
                    task._create_member_change_notifications(removed_user_ids=removed_user_ids)

        if 'custom_status' in vals:
            for task in self:
                if task.custom_status != old_status_map.get(task.id):
                    recipient_ids = set(task.user_ids.ids + task.assigned_user_ids.ids)
                    if recipient_ids:
                        task._create_status_change_notifications(recipient_ids)

        return result
