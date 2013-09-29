#!/usr/bin/env python3
from .base import BaseHandler


class LogoutHandler(BaseHandler):
    """
    Logout and clear cookie
    """
    def get(self):
        self.clear_cookie("statsmile_user")
        self.redirect("/")
        return