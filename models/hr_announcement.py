from odoo import fields, models


class HrAnnouncement(models.Model):
    _name = "hr.announcement"
    _description = "Announcements"
    _order = "id desc"

    active = fields.Boolean(default=True)
    is_important = fields.Boolean(default=False)
    name = fields.Html(required=True)
    title = fields.Char(required=True)


# class HrAnnouncementLegacy(models.Model):
#     _name = "hr.anousment"
#     _description = "Announcements"
#     _table = "hr_announcement"
#     _order = "id desc"
#
#     active = fields.Boolean(default=True)
#     name = fields.Char(required=True)
