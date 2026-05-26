"""
st_crm_helper.api.department
==============================
Whitelisted API methods consumed by the frontend department switcher widget,
form guard, and the department Link field dropdown on Lead/Deal forms.
"""
import frappe
from frappe import _
from st_crm_helper.overrides.department_filter import (
	_get_user_departments,
	_is_bypass_user,
	_is_dept_manager,
	_should_bypass,
)


@frappe.whitelist()
def get_my_departments() -> dict:
	"""
	Returns the current user's department context.

	Response shape:
	{
	    "bypass": true | false,       # true for admin OR manager
	    "is_manager": true | false,   # true only for dept managers (not full admins)
	    "departments": [...],         # depts this user belongs to
	    "all_departments": [...],     # all active depts (for bypass/manager users)
	}
	"""
	user = frappe.session.user
	is_bypass = _is_bypass_user(user)
	is_manager = _is_dept_manager(user)

	all_active = frappe.get_all(
		"CRM Department",
		filters={"is_active": 1},
		fields=["name"],
		order_by="department_name asc",
		ignore_permissions=True,
	)
	all_dept_names = [d.name for d in all_active]

	# Both admins and managers get full bypass — they see everything
	if is_bypass or is_manager:
		return {
			"bypass": True,
			"is_manager": is_manager and not is_bypass,
			"departments": all_dept_names,
			"all_departments": all_dept_names,
		}

	user_depts = _get_user_departments(user)
	return {
		"bypass": False,
		"is_manager": False,
		"departments": user_depts,
		"all_departments": user_depts,
	}


@frappe.whitelist()
def get_department_options() -> list:
	"""
	Returns departments available to the current user for the Link field dropdown
	on Lead/Deal/etc. forms.

	- Admin / manager → all active departments
	- Regular user    → only their own department(s)

	Returns list of {"value": name, "label": department_name} dicts.
	"""
	user = frappe.session.user

	all_active = frappe.get_all(
		"CRM Department",
		filters={"is_active": 1},
		fields=["name as value", "department_name as label"],
		order_by="department_name asc",
		ignore_permissions=True,
	)

	if _should_bypass(user):
		return all_active

	user_depts = _get_user_departments(user)
	return [d for d in all_active if d["value"] in user_depts]


@frappe.whitelist()
def get_all_departments() -> list:
	"""Returns all active CRM Departments. Used by admin-level selectors."""
	return frappe.get_all(
		"CRM Department",
		filters={"is_active": 1},
		fields=["name as value", "department_name as label"],
		order_by="department_name asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def get_department_members(department: str) -> list:
	"""Returns users assigned to a specific department. System Manager only."""
	if not frappe.has_permission("CRM Department", "read", department):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	return frappe.get_all(
		"CRM Department User",
		filters={"parent": department, "parenttype": "CRM Department"},
		fields=["user", "full_name", "is_manager"],
		ignore_permissions=True,
	)
