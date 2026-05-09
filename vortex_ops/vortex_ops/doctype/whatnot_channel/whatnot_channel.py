import frappe
from frappe.model.document import Document


class WhatnotChannel(Document):
    def validate(self):
        if self.whatnot_username:
            self.whatnot_username = self.whatnot_username.lstrip("@").lower()
        if self.whatnot_username and not self.channel_url:
            self.channel_url = (
                f"https://www.whatnot.com/user/{self.whatnot_username}"
            )
