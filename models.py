#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import json

import web

web.config.debug_sql = False
curdir = os.path.dirname(os.path.abspath(__file__))
db = web.database(dbn='sqlite', db=os.path.join(curdir, 'fanfou-m.db'))

if not os.path.exists(os.path.join(curdir, 'fanfou-m.db')):
    with open(os.path.join(curdir, 'fanfou-m.sql')) as f:
        for sql in f.read().strip().split(';'):
            db.query(sql)

session = web.session.DBStore(db, 'sessions')


class Consumer:
    def set(self, consumer_id, consumer_name, consumer, consumer_type='private'):
        try:
            db.insert('consumer', consumer_id=consumer_id, consumer_name=consumer_name, consumer=json.dumps(consumer), consumer_type=consumer_type)
        except:
            db.update('consumer', where="consumer_id = '%s'" % consumer_id, consumer_name=consumer_name, consumer=json.dumps(consumer))

    def get(self, consumer_id):
        res = db.query("select consumer_name, consumer from consumer where consumer_id = '%s'" % consumer_id).first()
        try:
            res['consumer'] = json.loads(res['consumer'])
        except:
            res = {'consumer': ''}
        return res

    def all(self):
        return db.query("select consumer_id, consumer_name from consumer where consumer_type = 'public'").list()


class Token:
    def set(self, token_id, consumer_id, token):
        try:
            db.insert('token', token_id=token_id, consumer_id=consumer_id, token=json.dumps(token))
        except:
            db.update('token', where="token_id='%s'" % token_id, consumer_id=consumer_id, token=json.dumps(token))

    def get(self, token_id):
        res = db.query("select t.token, c.consumer from token t, consumer c where c.consumer_id = t.consumer_id and t.token_id = '%s'" % token_id).first()
        try:
            res['consumer'] = json.loads(res['consumer'])
            res['token'] = json.loads(res['token'])
        except:
            res = {'consumer': '', 'token': ''}
        return res


class Conf:
    def set(self, user_id, blacklist):
        try:
            db.insert('conf', user_id=user_id, blacklist=json.dumps(blacklist))
        except:
            db.update('conf', where="user_id = '%s'" % user_id, blacklist=json.dumps(blacklist))

    def get(self, user_id):
        res = db.query("select blacklist from conf where user_id = '%s'" % user_id).first()
        try:
            res['blacklist'] = json.loads(res['blacklist'])
        except:
            res = {'blacklist': ''}
        return res


class Log:
    def set(self, referer, exc_info):
        db.insert('log', referer=referer, exc_info=exc_info)

    def get(self, limit=1):
        return db.query("select * from log ORDER BY atime DESC LIMIT %d" % limit).list()


class Ctx:
    def __getattr__(self, key):
        try:
            res = db.query("select val from ctx where key = '%s'" % key).first()
            return json.loads(res['val'])
        except TypeError:
            return None

    def __setattr__(self, key, val):
        try:
            db.insert('ctx', key=key, val=json.dumps(val))
        except:
            db.update('ctx', where="key = '%s'" % key, val=json.dumps(val))


consumer = Consumer()
token = Token()
conf = Conf()
log = Log()
ctx = Ctx()
