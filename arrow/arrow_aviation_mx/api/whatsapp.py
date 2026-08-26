# Copyright (c) 2026, osher and contributors
# WhatsApp integration via Hermes gateway

import frappe
import requests
import json
from frappe.utils import today, now_datetime


# Hermes gateway endpoint (on Windows, accessible via Tailscale)
HERMES_GATEWAY_URL = "http://100.87.188.7:5173"
HERMES_WEBHOOK_SECRET = "arrow-procurement-webhook-2026"


@frappe.whitelist()
def send_whatsapp_message(message):
	"""
	Send a WhatsApp message to Osher via Hermes gateway.
	
	The message is sent via HTTP POST to the Hermes gateway webhook endpoint,
	which then sends it through WhatsApp.
	
	Fallback: if the gateway is not reachable, the message is logged as an error
	and an email is sent instead.
	"""
	# Get phone number from ARROW MX Settings
	phone = "+972505511142"  # Osher's default
	try:
		settings = frappe.get_doc("ARROW MX Settings")
		if hasattr(settings, 'whatsapp_phone') and settings.whatsapp_phone:
			phone = settings.whatsapp_phone
	except Exception:
		pass

	try:
		# Try to send via Hermes gateway HTTP API
		response = requests.post(
			f"{HERMES_GATEWAY_URL}/api/send",
			json={
				"platform": "whatsapp",
				"target": phone,
				"message": message
			},
			headers={
				"Content-Type": "application/json",
				"X-Webhook-Secret": HERMES_WEBHOOK_SECRET
			},
			timeout=10
		)
		if response.status_code == 200:
			return {"success": True, "method": "gateway"}
		else:
			raise Exception(f"Gateway returned {response.status_code}")
	except Exception as e:
		# Fallback: log and send email
		frappe.log_error(
			f"WhatsApp send failed: {str(e)}\nMessage: {message}",
			"WhatsApp Notification"
		)
		# Send as email fallback
		try:
			frappe.sendmail(
				recipients=["noa992250@gmail.com", "oshermalul@gmail.com"],
				subject="WhatsApp Notification (fallback)",
				message=f"<pre>{message}</pre>"
			)
		except Exception:
			pass
		return {"success": False, "error": str(e), "fallback": "email"}


@frappe.whitelist()
def send_weekly_digest():
	"""
	Send a weekly WhatsApp digest of all open purchase orders.
	Called by the Frappe scheduler every Sunday at 9:00 AM.
	"""
	from arrow.arrow_aviation_mx.doctype.purchase_order.purchase_order import get_weekly_summary
	
	pos = get_weekly_summary()
	
	if not pos:
		return {"success": True, "message": "No open orders"}
	
	# Build digest message
	new_orders = [po for po in pos if po.get('status') == 'New']
	ordered = [po for po in pos if po.get('status') == 'Ordered']
	
	lines = [
		f"📋 *Weekly Procurement Summary*",
		f"📅 {today()}",
		f"",
		f"🆕 *New Orders ({len(new_orders)}):*"
	]
	
	for po in new_orders[:15]:
		urgency = " 🚨AOG" if po.get('urgency') == 'AOG' else ""
		supplier = f" → {po['supplier_name']}" if po.get('supplier_name') else ""
		lines.append(f"• {po['item_name']} ({po['part_number']}) qty {po['quantity']}{urgency}{supplier}")
	
	if len(new_orders) > 15:
		lines.append(f"... and {len(new_orders) - 15} more")
	
	lines.append(f"")
	lines.append(f"📦 *Ordered ({len(ordered)}):*")
	
	for po in ordered[:15]:
		supplier = f" ← {po['supplier_name']}" if po.get('supplier_name') else ""
		lines.append(f"• {po['item_name']} ({po['part_number']}) qty {po['quantity']}{supplier}")
	
	if len(ordered) > 15:
		lines.append(f"... and {len(ordered) - 15} more")
	
	lines.append(f"")
	lines.append(f"Total open: {len(pos)}")
	
	message = '\n'.join(lines)
	
	result = send_whatsapp_message(message)
	return {"success": result.get('success', False), "message": message, "result": result}
