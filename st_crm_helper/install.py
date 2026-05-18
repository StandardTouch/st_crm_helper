import os
import re
import frappe


def after_install():
	"""Run once when app is installed on a site."""
	_create_default_department()
	_patch_crm_index()


def after_migrate():
	"""Run after every bench migrate — safe to run repeatedly."""
	_patch_crm_index()


def _create_default_department():
	if not frappe.db.exists("CRM Department", "General"):
		doc = frappe.new_doc("CRM Department")
		doc.department_name = "General"
		doc.is_active = 1
		doc.insert(ignore_permissions=True)
		frappe.db.commit()


def _patch_crm_index():
	"""
	Inject ST CRM Helper scripts into the CRM frontend index.html.

	Frappe Cloud serves the CRM Vue app as a pre-built static file via nginx —
	override_html and base_template_hook have no effect there.
	This function directly patches the file on disk during install/migrate.

	- Safe to run repeatedly (idempotent — skips if already patched)
	- Works regardless of Vue bundle hash changes
	- Injects scripts BEFORE the <script type="module"> Vue bundle
	  so that window.fetch is patched before the first dashboard API call
	"""
	crm_index = os.path.abspath(
		os.path.join(
			frappe.get_app_path("crm"), "..", "public", "frontend", "index.html"
		)
	)

	if not os.path.exists(crm_index):
		print(f"[ST CRM] index.html not found at {crm_index} — skipping patch")
		return

	with open(crm_index, "r", encoding="utf-8") as f:
		content = f.read()

	# Already patched — skip
	if "st_crm_helper" in content:
		print("[ST CRM] index.html already patched — skipping")
		return

	inject = (
		"\n    <!-- ST CRM Helper: department filter scripts -->\n"
		'    <script src="/assets/st_crm_helper/js/department_filter.js"></script>\n'
		'    <script src="/assets/st_crm_helper/js/crm_dashboard_dept.js"></script>\n\n'
	)

	# Inject immediately before <script type="module" (the Vue bundle)
	patched = re.sub(
		r'(<script type="module")',
		inject + r"\1",
		content,
		count=1,
	)

	if patched == content:
		print("[ST CRM] Could not find injection point in index.html — skipping patch")
		return

	with open(crm_index, "w", encoding="utf-8") as f:
		f.write(patched)

	print("[ST CRM] index.html patched successfully ✓")
