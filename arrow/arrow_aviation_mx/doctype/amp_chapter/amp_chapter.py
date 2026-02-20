# Copyright (c) 2026, osher and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMPChapter(Document):
	def validate(self):
		self.validate_sort_order()

	def validate_sort_order(self):
		if not self.sort_order:
			self.sort_order = self.chapter_number * 10

	def get_tasks_ordered(self):
		"""Return chapter tasks ordered by sort_order then task_number."""
		tasks = sorted(self.chapter_tasks, key=lambda t: (t.sort_order or 0, t.task_number or ""))
		return tasks

	def get_task_notes(self):
		"""Get active task notes for this chapter."""
		return frappe.get_all(
			"AMP Task Note",
			filters={"chapter": self.name, "status": "Active"},
			fields=["*"],
			order_by="task_number asc",
		)
