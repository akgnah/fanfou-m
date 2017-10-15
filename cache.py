#!/usr/bin/python
# -*- coding: utf-8 -*-
import time


def statuses(obj, item):
    v = {
        'id': item['id'],
        'text': item['text'],
        'user': {'name': item['user']['name']},
        'ctime': time.time(),
    }
    k = item['id']
    obj[k] = v


def privatemsg(obj, item):
    if session.me['id'] == item['sender_id']:  # noqa
        sender = item['recipient_id']
    else:
        sender = item['sender_id']
    v = {
        'id': sender,
        'ctime': time.time(),
    }
    k1 = item.get('in_reply_to', {}).get('id')
    k2 = item['id']
    if k1:
        obj[k1] = v
    obj[k2] = v


def users(obj, item):
    if item.get('repost_status_id'):
        v = {
            'id': item['repost_user_id'],
            'name': item['repost_screen_name'],
            'ctime': time.time(),
        }
        k = item['repost_status_id']
        obj[k] = v
    elif item.get('photo'):
        v = {
            'id': item['user']['id'],
            'name': item['user']['name'],
            'ctime': time.time(),
        }
        k = item['id']
        obj[k] = v
    elif item.get('in_reply_to_status_id'):
        v = {
            'id': item['in_reply_to_user_id'],
            'name': item['in_reply_to_screen_name'],
            'ctime': time.time(),
        }
        k = item['in_reply_to_status_id']
        obj[k] = v


def users_profile(obj, item):
    k, v = item['id'], item
    try:
        del v['status']
    except:
        pass

    v['ctime'] = time.time()
    obj[k] = v


def truncate(d, size=64):
    items = sorted(d.items(), key=lambda x: x[1]['ctime'])
    return dict(items[-size:])


def save(session, data, keys):
    globals()['session'] = session
    for key in keys.split(','):
        func = globals().get(key)
        obj = session.get(key, {})
        for item in data:
            func(obj, item)
        session[key] = truncate(obj)
