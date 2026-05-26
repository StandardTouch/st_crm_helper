"""
st_crm_helper.overrides.department_filter
==========================================
Server-side department-based access control for all CRM doctypes.

Rules:
  - System Manager / Administrator  → bypass everything
  - User with is_manager = 1        → bypass everywhere (list, form, dashboard)
  - Regular user with departments   → filtered to their department(s)
  - Regular user with no departments → sees nothing (1=0)
"""
import frappe
from frappe import _

BYPASS_ROLES = frozenset({"System Manager", "Administrator"})
_CACHE_PREFIX = "st_crm_user_depts_"
_MANAGER_CACHE_PREFIX = "st_crm_is_manager_"


def _is_bypass_user(user: str) -> bool:
	"""Return True if the user should bypass all department filters."""
	if user in ("Administrator", "Guest"):
		return True
	return bool(set(frappe.get_roles(user)) & BYPASS_ROLES)


def _is_dept_manager(user: str) -> bool:
	"""
	Return True if the user has is_manager = 1 in ANY active CRM Department.
	Managers bypass all filters everywhere — list, form, and dashboard.
	Result is cached on frappe.local for the duration of the request.
	"""
	cache_key = f"{_MANAGER_CACHE_PREFIX}{user}"
	if hasattr(frappe.local, cache_key):
		return getattr(frappe.local, cache_key)

	rows = frappe.get_all(
		"CRM Department User",
		filters={"user": user, "is_manager": 1, "parenttype": "CRM Department"},
		fields=["parent"],
		ignore_permissions=True,
	)
	result = False
	for row in rows:
		if frappe.db.get_value("CRM Department", row.parent, "is_active"):
			result = True
			break

	setattr(frappe.local, cache_key, result)
	return result


def _should_bypass(user: str) -> bool:
	"""Return True if this user should skip all department filtering."""
	return _is_bypass_user(user) or _is_dept_manager(user)


def _get_user_departments(user: str) -> list:
	"""
	Return list of active CRM Department names the user belongs to.
	Result is cached on frappe.local for the duration of the request.
	"""
	cache_key = f"{_CACHE_PREFIX}{user}"
	if hasattr(frappe.local, cache_key):
		return getattr(frappe.local, cache_key)

	rows = frappe.get_all(
		"CRM Department User",
		filters={"user": user, "parenttype": "CRM Department"},
		fields=["parent"],
		ignore_permissions=True,
	)
	active = [
		r.parent
		for r in rows
		if frappe.db.get_value("CRM Department", r.parent, "is_active")
	]
	setattr(frappe.local, cache_key, active)
	return active


# ─── Hook: permission_query_conditions ────────────────────────────────────────

def get_permission_query_conditions(user: str = None) -> str:
	"""
	Injected for all 6 CRM doctypes.
	Returns a SQL WHERE fragment appended to every list/API query.
	"""
	user = user or frappe.session.user

	# Admins and managers see everything
	if _should_bypass(user):
		return ""

	departments = _get_user_departments(user)
	if not departments:
		return "1=0"

	escaped = ", ".join(frappe.db.escape(d) for d in departments)
	return f"`department` IN ({escaped})"


# ─── Hook: has_permission ─────────────────────────────────────────────────────

def has_permission(doc, ptype: str = "read", user: str = None) -> bool:
	"""
	Record-level access check called when a user opens a specific document.
	"""
	user = user or frappe.session.user

	# Admins and managers see everything
	if _should_bypass(user):
		return True

	departments = _get_user_departments(user)
	if not departments:
		return False

	record_dept = doc.get("department")

	# Legacy records with no department set — allow access
	if not record_dept:
		return True

	return record_dept in departments


# ─── Hook: doc_events before_insert ───────────────────────────────────────────

def set_department_on_insert(doc, method: str = None) -> None:
	"""
	Automatically sets the department field on new records.
	Uses the creating user's first active department as the default.
	Skipped if the field is already set or if the user is a bypass/manager user.
	"""
	if doc.get("department"):
		return  # Already set manually — respect it

	user = frappe.session.user

	# Admins and managers set department manually
	if _should_bypass(user):
		return

	departments = _get_user_departments(user)
	if departments:
		doc.department = departments[0]
