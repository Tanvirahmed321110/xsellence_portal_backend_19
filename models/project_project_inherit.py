from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'
    _order = 'create_date desc'

    # For Useful link links page
    github_link = fields.Char(string='Github Repo Link',tracking=True)
    live_link  = fields.Char(string='Live Link',tracking=True)
    live_user  = fields.Char(string='Live User',tracking=True)
    live_password  = fields.Char(string='Live Password',tracking=True)

    dev_link = fields.Char(string='Dev Server Link',tracking=True)
    dev_user = fields.Char(string='Dev Server User',tracking=True)
    dev_password = fields.Char(string='Dev Server Password',tracking=True)

    user_id = fields.Many2one(
        'res.users',
        tracking=True,
    )


    custom_priority = fields.Selection([
        ('normal','normal'),
        ('medium','medium'),
        ('high','high'),
        ('urgent','urgent'),
    ], string=' Priority',default='normal')

    custom_status = fields.Selection([
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Project Status', default='planning',tracking=True)

    # assign members
    assigned_user_ids = fields.Many2many(
        'res.users',
        string='Assigned Users',
        tracking=True
    )

    # 🔥 Remaining Days Field
    remaining_days = fields.Integer(
        string='Remaining Days',
        compute='_compute_remaining_days',
        readonly=True,
    )



    @api.depends('date')
    def _compute_remaining_days(self):
        today = fields.Date.context_today(self)

        for rec in self:
            if rec.date:
                rec.remaining_days = (rec.date - today).days
            else:
                rec.remaining_days = 0

    allocated_hours = fields.Float(
        compute="_compute_allocated_hours",
        store=True,
        readonly=False
    )

    @api.depends("date_start", "date")
    def _compute_allocated_hours(self):
        for rec in self:
            if rec.date_start and rec.date:
                delta = rec.date - rec.date_start
                rec.allocated_hours = delta.days * 8
            else:
                rec.allocated_hours = 0.0

    def _create_assignment_notifications(self, user_ids):
        Notification = self.env['xsellence.assignment.notification']

        for project in self:
            Notification.create_for_users(user_ids, {
                'title': 'Project Assigned',
                'description': 'You have been added to %s project.' % project.name,
                'view_url': '/projects/details/%s' % project.id,
                'res_model': 'project.project',
                'res_id': project.id,
            })

    def _create_status_change_notifications(self, user_ids):
        Notification = self.env['xsellence.assignment.notification']
        status_labels = dict(self._fields['custom_status'].selection)

        for project in self:
            status_label = status_labels.get(project.custom_status, project.custom_status)
            # Reuse the same notification model so popup and sidebar both
            # receive project status updates without any extra table.
            Notification.create_for_users(user_ids, {
                'title': 'Project Status Changed',
                'description': '%s project status changed to %s.' % (project.name, status_label),
                'view_url': '/projects/details/%s' % project.id,
                'res_model': 'project.project',
                'res_id': project.id,
            })

    def _create_member_change_notifications(self, added_user_ids=None, removed_user_ids=None):
        Notification = self.env['xsellence.assignment.notification']
        actor_name = self.env.user.name or 'A user'

        for project in self:
            if added_user_ids:
                Notification.create_for_users(added_user_ids, {
                    'title': 'Project Member Added',
                    'description': '%s added you to %s project.' % (actor_name, project.name),
                    'view_url': '/projects/details/%s' % project.id,
                    'res_model': 'project.project',
                    'res_id': project.id,
                })

            if removed_user_ids:
                Notification.create_for_users(removed_user_ids, {
                    'title': 'Project Member Removed',
                    'description': '%s removed you from %s project.' % (actor_name, project.name),
                    'view_url': '/projects/details/%s' % project.id,
                    'res_model': 'project.project',
                    'res_id': project.id,
                })

    def _create_comment_notifications(self, comment_author_name, comment_text):
        Notification = self.env['xsellence.assignment.notification']

        for project in self:
            recipient_ids = set(project.assigned_user_ids.ids + project.user_id.ids)
            if self.env.user.id:
                recipient_ids.discard(self.env.user.id)

            if not recipient_ids:
                continue

            comment_preview = (comment_text or '').strip().replace('\n', ' ')
            if len(comment_preview) > 120:
                comment_preview = comment_preview[:117] + '...'

            Notification.create_for_users(recipient_ids, {
                'title': 'Project Comment Added',
                'description': '%s commented on %s project: %s' % (comment_author_name, project.name, comment_preview),
                'view_url': '/projects/details/%s' % project.id,
                'res_model': 'project.project',
                'res_id': project.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)

        for project in projects:
            assigned_user_ids = set(project.assigned_user_ids.ids)
            if project.user_id:
                assigned_user_ids.add(project.user_id.id)

            if assigned_user_ids:
                project._create_assignment_notifications(assigned_user_ids)

        return projects

    def write(self, vals):
        old_user_map = {
            project.id: set(project.assigned_user_ids.ids + project.user_id.ids)
            for project in self
        }
        old_status_map = {
            project.id: project.custom_status
            for project in self
        }

        result = super().write(vals)

        if 'assigned_user_ids' in vals or 'user_id' in vals:
            for project in self:
                new_user_ids = set(project.assigned_user_ids.ids + project.user_id.ids)
                added_user_ids = new_user_ids - old_user_map.get(project.id, set())
                removed_user_ids = old_user_map.get(project.id, set()) - new_user_ids

                if added_user_ids:
                    project._create_assignment_notifications(added_user_ids)
                    project._create_member_change_notifications(added_user_ids=added_user_ids)

                if removed_user_ids:
                    project._create_member_change_notifications(removed_user_ids=removed_user_ids)

        if 'custom_status' in vals:
            for project in self:
                if project.custom_status != old_status_map.get(project.id):
                    recipient_ids = set(project.assigned_user_ids.ids + project.user_id.ids)
                    if recipient_ids:
                        project._create_status_change_notifications(recipient_ids)

        return result
