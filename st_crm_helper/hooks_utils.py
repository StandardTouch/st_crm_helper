import frappe


def after_request(response):
	"""
	Frappe after_request hook — injects ST CRM Helper scripts into the
	CRM frontend HTML response in memory.

	This is the only reliable method on Frappe Cloud because:
	- app_include_js / web_include_js only affect Frappe Desk (ERPNext), not the CRM Vue SPA
	- override_html / base_template_hook are ignored when nginx serves static files directly
	- Patching files on disk is fragile and breaks on redeploy

	This hook intercepts the HTTP response for /crm* pages and injects
	our scripts before the Vue bundle <script type="module"> tag.
	"""
	try:
		# Only process HTML responses for the CRM frontend
		if not _is_crm_html_response(response):
			return response

		content = response.get_data(as_text=True)

		# Already injected (cached response) — skip
		if "st_crm_helper" in content:
			return response

		inject = (
			'\n    <!-- ST CRM Helper: department filter -->\n'
			'    <script src="/assets/st_crm_helper/js/department_filter.js"></script>\n'
			'    <script src="/assets/st_crm_helper/js/crm_dashboard_dept.js"></script>\n'
		)

		# Inject before <script type="module" (the Vue bundle) so fetch is
		# patched before the first dashboard API call fires
		if '<script type="module"' in content:
			patched = content.replace(
				'<script type="module"',
				inject + '    <script type="module"',
				1,
			)
			response.set_data(patched)

	except Exception:
		# Never break the response — silently pass on any error
		pass

	return response


def _is_crm_html_response(response):
	"""Return True only for CRM frontend HTML page responses."""
	try:
		# Must be a successful HTML response
		if response.status_code != 200:
			return False
		content_type = response.content_type or ""
		if "text/html" not in content_type:
			return False
		# Must be a CRM page request
		path = frappe.request.path if frappe.request else ""
		if not path.startswith("/crm"):
			return False
		return True
	except Exception:
		return False
