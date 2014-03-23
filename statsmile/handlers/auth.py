#!/usr/bin/env python3

from datetime import datetime

from motor import Op
from tornado import gen
from tornado.auth import OpenIdMixin
from tornado.gen import engine
from tornado.escape import json_encode
from tornado.web import asynchronous, HTTPError

from statsmile.common import get_user, json_code
from .base import BaseHandler


class AuthLoginHandler(BaseHandler, OpenIdMixin):

    _OPENID_ENDPOINT = "http://steamcommunity.com/openid/login"

    @asynchronous
    @gen.coroutine
    def get(self):

        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user()

            if not user:
                raise HTTPError(500, "Steam Auth Failed")

            rv = yield Op(self.db.users.find_one, {'steam_id': user['claimed_id'][-17:]})
            temp = self.upd_session()

            if not rv:
                userid = yield get_user(self.settings['api_key'], user['claimed_id'][-17:])
                self.db.users.insert(userid)
                temp['user_id'] = userid['_id']
                temp['signed_in'] = datetime.now()
                self.db.sessions.insert(temp)

            else:
                temp['user_id'] = rv['_id']
                temp['signed_in'] = datetime.now()
                self.db.sessions.insert(temp)

            self.set_secure_cookie('user_session', json_encode(str(temp['_id'])))
            self.redirect(self.get_argument('next', '/'))
            return
        else:
            yield self.authenticate_redirect()


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.db.sessions.remove({'_id': self.current_user['_id']})
        self.clear_cookie('user_session')
        self.redirect(self.get_argument('next', '/'))


class AuthHandler(BaseHandler):

    def prepare(self):
        super().prepare()
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    @asynchronous
    @engine
    def get(self):
        if self.current_user:
            session = yield Op(self.db.users.find_one, {'_id': self.current_user['user_id']})
            self.write(json_code.json_encode({'auth': True, 'user': session}))
            self.finish()
            return
        self.write(json_code.json_encode({'auth': False, 'user': None}))
        self.finish()
        return