# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import base64
import os

import frappe


def get_logo_base64(doc):
	"""Convert the AMP Document's logo to a base64 data URI for embedding in HTML/PDF."""
	if not doc.logo:
		return ""

	file_path = doc.logo
	if file_path.startswith("/files/"):
		site_path = frappe.get_site_path("public", file_path.lstrip("/"))
	elif file_path.startswith("/private/files/"):
		site_path = frappe.get_site_path(file_path.lstrip("/"))
	else:
		return ""

	if not os.path.exists(site_path):
		return ""

	ext = os.path.splitext(site_path)[1].lower()
	mime_types = {
		".png": "image/png",
		".jpg": "image/jpeg",
		".jpeg": "image/jpeg",
		".gif": "image/gif",
		".svg": "image/svg+xml",
	}
	mime = mime_types.get(ext, "image/png")

	with open(site_path, "rb") as f:
		encoded = base64.b64encode(f.read()).decode("utf-8")

	return f"data:{mime};base64,{encoded}"


def format_date(date_val, fmt="dd.MM.yyyy"):
	"""Format a date value for display in the AMP document."""
	if not date_val:
		return ""
	return frappe.utils.formatdate(date_val, fmt)


def get_registration_list(doc):
	"""Get comma-separated list of active registrations."""
	regs = [r.registration for r in doc.registrations if r.active]
	return ", ".join(regs)


def get_serial_number_list(doc):
	"""Get comma-separated list of serial numbers for active registrations."""
	serials = [r.serial_number for r in doc.registrations if r.active]
	return ", ".join(serials)


def get_all_chapters(amp_document_name):
	"""Get all chapters for an AMP Document, ordered by sort_order."""
	chapters = frappe.get_all(
		"AMP Chapter",
		filters={"amp_document": amp_document_name},
		fields=["name"],
		order_by="sort_order asc, chapter_number asc",
	)
	# Load full documents to get child tables
	return [frappe.get_doc("AMP Chapter", ch.name) for ch in chapters]


def get_all_revisions(amp_document_name):
	"""Get all revisions for an AMP Document, ordered by date."""
	return frappe.get_all(
		"AMP Revision",
		filters={"amp_document": amp_document_name},
		fields=["*"],
		order_by="revision_date asc",
	)


def get_active_task_notes(amp_document_name):
	"""Get all active task notes for an AMP Document."""
	return frappe.get_all(
		"AMP Task Note",
		filters={"amp_document": amp_document_name, "status": "Active"},
		fields=["*"],
		order_by="chapter asc, task_number asc",
	)


def build_task_notes_map(task_notes):
	"""
	Build a nested dict mapping chapter_name -> task_number -> [notes]
	for efficient lookup during PDF rendering.
	"""
	notes_map = {}
	for note in task_notes:
		chapter_key = note.get("chapter") or "__general__"
		task_key = note.get("task_number") or "__general__"
		if chapter_key not in notes_map:
			notes_map[chapter_key] = {}
		if task_key not in notes_map[chapter_key]:
			notes_map[chapter_key][task_key] = []
		notes_map[chapter_key][task_key].append(note)
	return notes_map


def build_lep_entries(chapters):
	"""Build List of Effective Pages entries from chapter data."""
	entries = []
	for ch in chapters:
		entries.append(
			{
				"title": ch.title,
				"chapter_number": ch.chapter_number,
				"revision": ch.revision or "0",
				"revision_date_formatted": format_date(ch.revision_date) if ch.revision_date else "",
			}
		)
	return entries


def format_revision_dates(revisions):
	"""Add formatted date fields to revision records."""
	for rev in revisions:
		rev["revision_date_formatted"] = format_date(rev.get("revision_date"))
		rev["approval_date_formatted"] = format_date(rev.get("approval_date"))
	return revisions
