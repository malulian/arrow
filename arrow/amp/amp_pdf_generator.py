# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

"""
AMP PDF Generator

Generates complete Aircraft Maintenance Program documents as PDF files
using WeasyPrint (preferred) or wkhtmltopdf as fallback.
"""

import os

import frappe
from frappe.utils import get_site_path
from jinja2 import BaseLoader, Environment

from arrow.amp.amp_utils import (
	build_lep_entries,
	build_task_notes_map,
	format_date,
	format_revision_dates,
	get_active_task_notes,
	get_all_chapters,
	get_all_revisions,
	get_logo_base64,
	get_registration_list,
	get_serial_number_list,
)


def _get_template_path():
	"""Get the path to AMP templates directory."""
	app_path = frappe.get_app_path("arrow")
	return os.path.join(app_path, "templates", "amp")


def _load_css():
	"""Load the AMP PDF CSS stylesheet."""
	css_path = os.path.join(_get_template_path(), "amp_pdf.css")
	if os.path.exists(css_path):
		with open(css_path) as f:
			return f.read()
	return ""


def _load_template(template_name):
	"""Load a Jinja template from the AMP templates directory."""
	template_path = os.path.join(_get_template_path(), template_name)
	if os.path.exists(template_path):
		with open(template_path) as f:
			return f.read()
	return ""


def _build_context(doc):
	"""Build the full template context for PDF rendering."""
	# Load all data
	all_chapters = get_all_chapters(doc.name)
	all_revisions = get_all_revisions(doc.name)
	task_notes = get_active_task_notes(doc.name)

	# Format revision dates
	all_revisions = format_revision_dates(all_revisions)

	# Separate chapters by section type
	intro_chapters = [ch for ch in all_chapters if ch.section_type == "Introduction"]
	report_chapters = [ch for ch in all_chapters if ch.section_type == "Report"]

	# Separate revisions by type
	regular_revisions = [r for r in all_revisions if r.get("revision_type") == "Regular"]
	temporary_revisions = [r for r in all_revisions if r.get("revision_type") == "Temporary"]
	all_revisions_with_highlights = [r for r in all_revisions if r.get("highlights")]

	# Build task notes map
	chapter_task_notes = build_task_notes_map(task_notes)

	# Build LEP entries
	lep_entries = build_lep_entries(all_chapters)

	# Logo as base64
	logo_base64 = get_logo_base64(doc)

	# Registration and serial number lists
	registration_list = get_registration_list(doc)
	serial_number_list = get_serial_number_list(doc)

	# Revision info
	latest_revision = all_revisions[-1] if all_revisions else None
	revision_date_formatted = format_date(doc.current_revision_date)

	# Pre-render the preface header HTML for use in auto-generated pages
	preface_header_html = _render_preface_header(doc, logo_base64, registration_list, serial_number_list)

	return {
		"doc": doc,
		"css": _load_css(),
		"all_chapters": all_chapters,
		"intro_chapters": intro_chapters,
		"report_chapters": report_chapters,
		"all_revisions": all_revisions,
		"regular_revisions": regular_revisions,
		"temporary_revisions": temporary_revisions,
		"all_revisions_with_highlights": all_revisions_with_highlights,
		"chapter_task_notes": chapter_task_notes,
		"lep_entries": lep_entries,
		"logo_base64": logo_base64,
		"registration_list": registration_list,
		"serial_number_list": serial_number_list,
		"latest_revision": latest_revision,
		"revision_date_formatted": revision_date_formatted,
		"current_revision": doc.current_revision or "0",
		"amp_header_preface_rendered": preface_header_html,
		"frappe": frappe,
	}


def _render_preface_header(doc, logo_base64, registration_list, serial_number_list):
	"""Render the preface header HTML snippet."""
	return f"""<table class="header-preface">
		<tr class="header-title-row">
			<td colspan="4">AIRCRAFT MAINTENANCE PROGRAM</td>
			<td class="header-logo" rowspan="2">
				{'<img src="' + logo_base64 + '" alt="Logo">' if logo_base64 else ''}
			</td>
		</tr>
		<tr class="header-detail-row">
			<td>PREFACE</td>
			<td>{doc.aircraft_type}</td>
			<td>{registration_list}</td>
			<td>{serial_number_list}</td>
		</tr>
	</table>"""


def _render_html(doc):
	"""Render the complete AMP document as HTML."""
	template_source = _load_template("amp_document.html")
	context = _build_context(doc)

	# Use Jinja2 environment with custom include_raw tag support
	env = Environment(loader=BaseLoader())

	# Register include_raw as a simple variable substitution
	# The template uses {% include_raw "var_name" %} but we'll handle it
	# by replacing the include_raw tags with the actual content before rendering
	template_source = template_source.replace(
		'{% include_raw "amp_header_preface_rendered" %}',
		context["amp_header_preface_rendered"],
	)

	template = env.from_string(template_source)
	return template.render(**context)


def _html_to_pdf_weasyprint(html_content):
	"""Convert HTML to PDF using WeasyPrint."""
	try:
		from weasyprint import HTML

		pdf_bytes = HTML(string=html_content).write_pdf()
		return pdf_bytes
	except ImportError:
		frappe.throw(
			"WeasyPrint is not installed. Install it with: pip install weasyprint"
		)
	except Exception as e:
		frappe.throw(f"WeasyPrint PDF generation failed: {e!s}")


def _html_to_pdf_pdfkit(html_content):
	"""Fallback: Convert HTML to PDF using pdfkit/wkhtmltopdf."""
	try:
		import pdfkit

		options = {
			"page-size": "A4",
			"orientation": "Landscape",
			"margin-top": "20mm",
			"margin-bottom": "25mm",
			"margin-left": "15mm",
			"margin-right": "15mm",
			"encoding": "UTF-8",
			"enable-local-file-access": "",
		}
		pdf_bytes = pdfkit.from_string(html_content, False, options=options)
		return pdf_bytes
	except ImportError:
		frappe.throw(
			"Neither WeasyPrint nor pdfkit is installed. "
			"Install WeasyPrint with: pip install weasyprint"
		)
	except Exception as e:
		frappe.throw(f"pdfkit PDF generation failed: {e!s}")


def _save_pdf_file(doc, pdf_bytes):
	"""Save the PDF file and return the file URL."""
	filename = f"{doc.document_number or doc.name}_Rev{doc.current_revision or '0'}.pdf"
	# Sanitize filename
	filename = filename.replace(" ", "_").replace("/", "-")

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": pdf_bytes,
			"attached_to_doctype": "AMP Document",
			"attached_to_name": doc.name,
			"is_private": 1,
		}
	)
	file_doc.save(ignore_permissions=True)
	return file_doc.file_url


@frappe.whitelist()
def generate_amp_pdf(amp_document):
	"""
	Generate complete AMP document as PDF.

	Args:
		amp_document: Name of the AMP Document

	Returns:
		URL to the generated PDF file
	"""
	doc = frappe.get_doc("AMP Document", amp_document)

	# Render HTML
	html_content = _render_html(doc)

	# Try WeasyPrint first, fall back to pdfkit
	try:
		pdf_bytes = _html_to_pdf_weasyprint(html_content)
	except Exception:
		pdf_bytes = _html_to_pdf_pdfkit(html_content)

	# Save and return URL
	file_url = _save_pdf_file(doc, pdf_bytes)

	frappe.msgprint(
		f"AMP PDF generated: {file_url}",
		title="PDF Generated",
		indicator="green",
	)

	return file_url


@frappe.whitelist()
def preview_chapter(chapter_name):
	"""
	Generate an HTML preview of a single chapter.

	Args:
		chapter_name: Name of the AMP Chapter

	Returns:
		HTML string for preview
	"""
	chapter = frappe.get_doc("AMP Chapter", chapter_name)
	doc = frappe.get_doc("AMP Document", chapter.amp_document)

	logo_base64 = get_logo_base64(doc)
	registration_list = get_registration_list(doc)
	serial_number_list = get_serial_number_list(doc)
	css = _load_css()

	# Get task notes for this chapter
	task_notes = frappe.get_all(
		"AMP Task Note",
		filters={"chapter": chapter.name, "status": "Active"},
		fields=["*"],
	)
	task_notes_map = {}
	for note in task_notes:
		key = note.get("task_number") or "__general__"
		if key not in task_notes_map:
			task_notes_map[key] = []
		task_notes_map[key].append(note)

	# Build preview context
	context = {
		"doc": doc,
		"chapter": chapter,
		"css": css,
		"logo_base64": logo_base64,
		"registration_list": registration_list,
		"serial_number_list": serial_number_list,
		"task_notes": task_notes_map,
		"tasks": chapter.get_tasks_ordered() if hasattr(chapter, "get_tasks_ordered") else chapter.chapter_tasks,
	}

	# Render header
	if chapter.header_style == "Preface":
		header_html = f"""<table class="header-preface">
			<tr class="header-title-row">
				<td colspan="4">AIRCRAFT MAINTENANCE PROGRAM</td>
				<td class="header-logo" rowspan="2">
					{'<img src="' + logo_base64 + '" alt="Logo">' if logo_base64 else ''}
				</td>
			</tr>
			<tr class="header-detail-row">
				<td>{chapter.title.upper()}</td>
				<td>{doc.aircraft_type}</td>
				<td>{registration_list}</td>
				<td>{serial_number_list}</td>
			</tr>
		</table>"""
	else:
		header_html = f"""<table class="header-report">
			<tr>
				<td class="section-title">{chapter.title.upper()}</td>
				<td>{doc.aircraft_type}</td>
				<td>{serial_number_list}</td>
				<td>{registration_list}</td>
			</tr>
		</table>"""

	# Render content based on type
	content_html = ""
	if chapter.content_type == "Rich Text":
		content_html = f'<div class="rich-content">{chapter.content or ""}</div>'
	elif chapter.content_type == "Custom HTML":
		content_html = chapter.custom_html or ""
	elif chapter.content_type in ("Task Table", "Component Table", "Checklist"):
		template_map = {
			"Task Table": "amp_task_table.html",
			"Component Table": "amp_component_table.html",
			"Checklist": "amp_checklist.html",
		}
		template_source = _load_template(template_map[chapter.content_type])
		env = Environment(loader=BaseLoader())
		template = env.from_string(template_source)
		content_html = template.render(**context)

	# Compose full preview
	html = f"""<!DOCTYPE html>
<html>
<head>
	<meta charset="utf-8">
	<title>Preview: {chapter.title}</title>
	<style>{css}</style>
	<style>
		body {{ margin: 20px; }}
		@page {{ size: A4 landscape; margin: 15mm; }}
	</style>
</head>
<body>
	{header_html}
	{content_html}
</body>
</html>"""

	return html
