# Xsellence Portal — Odoo 19 Migration

Module version: `19.0.1.0.0`

## Migration changes

- Converted Odoo 18 JSON controller routes from `type="json"` to Odoo 19 `type="jsonrpc"`.
- Migrated custom user groups to the Odoo 19 `res.groups.privilege` structure.
- Removed the redundant Employee “Create User” view override because Odoo 19 already provides that action.
- Corrected the invalid `tpe="http"` controller argument.
- Restricted project, task, timesheet, profile, and helpdesk portal pages to authenticated users.
- Fixed duplicated controller method names and duplicated timesheet conversion logic.
- Fixed project Live User and Live Password form mappings.
- Removed duplicate model field declaration and development/cache files.
- Corrected broken static asset paths and added a bundled default user avatar.
- Replaced the copied project form on the Create Ticket page with an optional Odoo Helpdesk integration.
- Updated the manifest, version, metadata, and installability flags for Odoo 19.

## Deployment

1. Copy `xsellence_portal` into the Odoo 19 custom addons directory.
2. Restart the Odoo 19 service.
3. Update the Apps list.
4. Install or upgrade **Xsellence Portal**.
5. Assign one Xsellence Portal access level to each relevant user.

## Validation scope

Python, XML, JavaScript, manifest, route, and ZIP integrity checks were performed. A live Odoo 19 database installation was not available in the conversion environment, so install the module first in a staging database before production deployment.
