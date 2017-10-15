#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import os
import time
import uuid
import random
import urllib2
import datetime
import mimetypes
import traceback

import web
import fanfou

import urls
import cache
import models

curdir = os.path.dirname(os.path.abspath(__file__))


class Utils:
    def gen_uuid(self, d):
        s = ''.join([str(v) for v in d.values()])
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))

    def nonce(self, d=8):
        digs = range(48, 58) + range(65, 91) + range(97, 123)
        chrs = [chr(random.choice(digs)) for i in range(d)]
        return ''.join(chrs)

    def format_time(self, s):
        then = datetime.datetime.strptime(s, '%a %b %d %H:%M:%S +0000 %Y')
        delta = datetime.datetime.utcnow() - then
        if delta.days < 1:
            if delta.seconds < 60:
                s = '%s 秒前' % delta.seconds
            elif 60 <= delta.seconds < 3600:
                s = '%d 分钟前' % (delta.seconds / 60.0)
            else:
                s = '约 %d 小时前' % (delta.seconds / 3600.0)
        else:
            s = (then + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
        return s

    def format_birthday(self, s):
        year, month, day = s.split('-')
        s = u''
        if int(year):
            s += u'%s 年 ' % int(year)
        if int(month):
            s += u'%s 月 ' % int(month)
        if int(day):
            s += u'%s 日' % day
        return s

    def html_encode(self, s):
        el = {'&lt;': '<', '&gt;': '>', '&quot;': '"', '&amp;': '&'}
        for k, v in el.items():
            s = s.replace(k, v)
        return s

    def replace_kw(self, s):
        s = re.sub('<b>([^<]*)</b>', lambda m: '<strong>%s</strong>' % m.groups()[0], s)
        return s.replace('http://fanfou.com', '')

    def get_source(self, s):
        p = re.compile(r'<[^>]*>(.*?)</a>')
        m = re.search(p, s)
        s = (m and m.groups()[0]) or s
        return ' ' + s if s[0] < u'\u0080' else s    # 0x80 is 128

    def get_msg_id(self, item):
        return item.get('repost_status_id') or item['id']

    def authorize(self):
        exclude = ('/callback', '/authorize', '/autologin', '/help', '/share')
        if session.get('consumer') and session.get('token'):
            return
        if web.ctx.env.get('PATH_INFO') in exclude:
            return
        raise web.seeother('/authorize')

    @property
    def client(self):
        client = fanfou.OAuth(session.consumer, session.token)
        fanfou.bound(client)
        return client

    def token_verify(self, token):
        session.consumer = token['consumer']
        session.token = token['token']
        self.client.account.verify_credentials()

    def fetch_tail(self, consumer):
        try:
            client = fanfou.XAuth(consumer, 'username', 'password')
            body = {'status': 'test %s' % time.time()}
            data = client.request('/statuses/update', 'POST', body).json()
            return self.get_source(data['source']).strip()
        except:
            return 'unknown'

    def tail(self):
        if not session.get('tail'):
            cid = self.gen_uuid(session.consumer)
            session.tail = models.consumer.get(cid)['consumer_name']
        return session.tail

    def cache(self, data, keys):
        if isinstance(data, list):
            cache.save(session, data, keys)
        else:
            cache.save(session, [data], keys)

    def refresh_cache(self, keys, _id=None):
        for key in keys.split(','):
            try:
                try:
                    del session[key][_id]
                except:
                    del session[key]
            except:
                continue

    def privatemsg_show(self, body={}):
        msg_id = body['id']
        user_id = session.privatemsg.get(msg_id)['id']
        body['id'] = user_id
        body['page'] = 1
        while 1:
            data = self.client.direct_messages.conversation(body).json()
            self.cache(data, 'privatemsg')
            msg_ids = [item['id'] for item in data]
            if msg_id in msg_ids:
                break
            if not data:
                break
            body['page'] += 1
        return data[msg_ids.index(msg_id)] if data else {}

    def friend_add(self, body={}):
        try:
            http_code = self.client.friendships.create(body).code
        except urllib2.HTTPError:
            http_code = 403
        return http_code

    def album(self, body={}):
        data = self.client.photos.user_timeline(body).json()
        self.cache(data, 'users,statuses')
        if data:
            self.photo_navigate(data[-1]['id'])
        return data

    def photo_navigate(self, msg_id):
        user_id = session.users.get(msg_id)['id']
        photo_ids = session.get('photo_ids', {})
        msg_ids = photo_ids.get(user_id, [])
        body = {'id': user_id, 'mode': 'lite', 'page': 1, 'count': 60}
        if msg_ids:
            data = self.client.photos.user_timeline(body).json()
            self.cache(data, 'users,statuses')
            if data[0]['id'] != msg_ids[0]:
                msg_ids = [item['id'] for item in data]
        stop = int(len(msg_ids) / 60.0)
        msg_ids = msg_ids[:stop * 60]
        body['page'] = stop
        while msg_id not in msg_ids or msg_id == msg_ids[-1]:
            body['page'] += 1
            data = self.client.photos.user_timeline(body).json()
            self.cache(data, 'users,statuses')
            msg_ids.extend([item['id'] for item in data])
            if not data:
                break

        idx = msg_ids.index(msg_id)
        last_id = msg_ids[idx - 1] if msg_id != msg_ids[0] else 0
        next_id = msg_ids[idx + 1] if msg_id != msg_ids[-1] else 0
        nav = (last_id, msg_id, next_id)
        photo_ids[user_id] = msg_ids
        session.photo_ids = photo_ids
        return idx, nav

    def users_show(self, body={}):
        data = session.get('users_profile', {}).get(body['id'])
        if not data:
            data = self.client.users.show(body).json()
            visible = data['following'] or not data['protected']
            data['visible'] = visible or body['id'] == self.me['id']
            self.cache(data, 'users_profile')
        return data

    def msg_show(self, body={}, raw=False):
        try:
            data = session.get('statuses', {}).get(body['id'])
            if not data or raw:
                data = self.client.statuses.show(body).json()
                self.cache(data, 'users,statuses')
        except urllib2.HTTPError as msg:
            session.http = str(msg)
            data = {}
        return data

    def trends(self):
        now = datetime.datetime.now()
        if not models.ctx.trends or now.minute % 10 == 0:
            models.ctx.trends = self.client.trends.list().json()['trends']
        return models.ctx.trends

    @property
    def notice(self):
        notice = self.client.account.notification({'mode': 'lite'}).json()
        notice['action'] = session.pop('action', '')
        notice['trends'] = self.trends()
        return notice

    @property
    def me(self):
        if not session.get('me'):
            data = self.client.users.show({'mode': 'lite'}).json()
            session.me = {'id': data['id'], 'name': data['name']}
        return session.me

    def blacklist(self):
        if not session.get('conf'):
            conf = models.conf.get(self.me['id'])
            session.conf = {'blacklist': filter(lambda x: x, conf['blacklist'])}
        return session.conf['blacklist']

    def blocked(self, text):
        if True in map(lambda s: s in text, self.blacklist()):
            return True

    def now(self):
        now = datetime.datetime.now()
        return now.strftime('%y/%m/%d %H:%M')

    def gif(self, item):
        return 'gif' if item['photo']['largeurl'][-3:].lower() == 'gif' else ''

    def notfound(self):
        referer = web.ctx.env.get('HTTP_REFERER', web.ctx.home)
        referer = referer.replace(web.ctx.home, '')
        return web.notfound(render.unrealized(self.me, 404, referer, ''))

    def internalerror(self):
        exc_info = traceback.format_exc()
        referer = web.ctx.env.get('HTTP_REFERER', web.ctx.home)
        if 'HTTP Error 404: Not Found' in exc_info:
            referer = referer.replace(web.ctx.home, '')
            return web.notfound(render.unrealized(self.me, 404, referer, ''))
        elif 'HTTP Error 401: Unauthorized' in exc_info:
            session.kill()
            web.setcookie('sid', '', 2592000)
            return web.internalerror(render.unrealized(self.me, 401, '/authorize', ''))
        elif 'HTTP Error 400: Bad Request' in exc_info:
            data = self.client.account.rate_limit_status().json()
            referer = referer.replace(web.ctx.home, 'http://m.fanfou.com')
            reset_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['reset_time_in_seconds']))
            return web.internalerror(render.unrealized(self.me, 400, referer, reset_time))
        else:
            referer = referer.replace(web.ctx.home, '')
            models.log.set(referer, exc_info)
            return web.internalerror(render.unrealized(self.me, 500, referer, ''))


utils = Utils()


class favicon_ico:
    def GET(self):
        web.header('Content-Type', 'image/x-icon;charset=utf-8')
        return open(os.path.join(curdir, 'static', 'favicon.ico'), 'rb').read()


class home:
    def GET(self, page=1):
        body = {'page': page, 'format': 'html', 'mode': 'lite', 'count': 15}
        data = utils.client.statuses.home_timeline(body).json()
        utils.cache(data, 'users,statuses')
        return render.home(utils.me, data, int(page), utils.notice)

    def POST(self):
        wi = web.input()
        if not wi.get('content'):
            session.action = '消息发送失败，请输入消息内容！'
            raise web.seeother('/home')
        elif wi.get('content') == session.get('last'):
            session.action = '请勿发重复消息！'
            raise web.seeother('/home')
        session.last = wi.content
        body = {'status': wi.content}
        utils.client.statuses.update(body)
        session.action = '发送成功！'
        raise web.seeother('/home')


class msg_reply:
    def GET(self, msg_id):
        body = {'id': msg_id, 'mode': 'lite', 'format': 'html'}
        return render.msg_reply(utils.me, utils.msg_show(body))

    def POST(self, msg_id):
        wi = web.input()
        body = {'status': wi.content, 'in_reply_to_status_id': msg_id}
        utils.client.statuses.update(body)
        session.action = '发送成功！'
        raise web.seeother('/home')


class msg_forward:
    def GET(self, msg_id):
        body = {'id': msg_id, 'mode': 'lite', 'format': 'html'}
        return render.msg_forward(utils.me, utils.msg_show(body))

    def POST(self, msg_id):
        wi = web.input()
        body = {'status': wi.content, 'repost_status_id': msg_id}
        utils.client.statuses.update(body)
        session.action = '发送成功！'
        raise web.seeother('/home')


class msg_new:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        return render.msg_new(utils.me, user)

    def POST(self, user_id):
        wi = web.input()
        body = {'status': wi.content, 'in_reply_to_user_id': user_id}
        utils.client.statuses.update(body)
        session.action = '发送成功！'
        raise web.seeother('/home')


class msg_del:
    def GET(self, msg_id):
        referer = web.ctx.env.get('HTTP_REFERER', '/home')
        referer = referer.replace(web.ctx.home, '')
        return render.msg_del(utils.me, msg_id, referer)

    def POST(self, msg_id):
        utils.client.statuses.destroy({'id': msg_id})
        session.action = '消息删除成功！'
        raise web.seeother(web.input().referer)


class msg_favorite_add:
    def GET(self, msg_id):
        try:
            utils.client.favorites.create({'id': msg_id})
        except urllib2.HTTPError:
            session.action = '收藏失败，此消息不公开。'
        referer = web.ctx.env.get('HTTP_REFERER', '/home')
        raise web.seeother(referer)


class msg_favorite_del:
    def GET(self, msg_id):
        utils.client.favorites.destroy({'id': msg_id})
        referer = web.ctx.env.get('HTTP_REFERER', '/home')
        raise web.seeother(referer)


class favorites:
    def GET(self, user_id, page=1):
        body = {'id': user_id, 'count': 15, 'page': page, 'mode': 'lite', 'format': 'html'}
        user = utils.users_show({'id': user_id})
        if user['visible']:
            data = utils.client.favorites(body).json()
            utils.cache(data, 'users')
        else:
            data = []
        return render.favorites(utils.me, user, data, int(page), utils.notice)


class friend_request:
    def GET(self, page=1):
        body = {'count': 10, 'page': page}
        data = utils.client.friendships.requests(body).json()
        return render.friend_request(utils.me, data, int(page), utils.notice)


class friend_acceptadd:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        return render.friend_acceptadd(utils.me, user)

    def POST(self, user_id):
        body = {'id': user_id}
        utils.client.friendships.accept(body)
        utils.client.friendships.create(body)
        if utils.notice['friend_requests']:
            raise web.seeother('/friend.request')
        else:
            raise web.seeother('/home')


class friend_accept:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        return render.friend_accept(utils.me, user)

    def POST(self, user_id):
        body = {'id': user_id}
        utils.client.friendships.accept(body)
        if utils.notice['friend_requests']:
            raise web.seeother('/friend.request')
        else:
            raise web.seeother('/home')


class friend_deny:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        return render.friend_deny(utils.me, user)

    def POST(self, user_id):
        body = {'id': user_id}
        utils.client.friendships.deny(body)
        if utils.notice['friend_requests']:
            raise web.seeother('/friend.request')
        else:
            raise web.seeother('/home')


class friend_add:
    def GET(self, user_id):
        referer = web.ctx.env.get('HTTP_REFERER', '/home')
        referer = referer.replace(web.ctx.home, '')
        user = utils.users_show({'id': user_id})
        return render.friend_add(utils.me, user, referer)

    def POST(self, user_id):
        wi = web.input()
        body = {'id': user_id}
        if utils.friend_add(body) == 403:
            session.action = u'已向 %s 发出关注请求，请等待确认。' % wi.name
        else:
            utils.refresh_cache('users_profile', user_id)
            session.action = u'你已成功关注 %s' % wi.name
        raise web.seeother(wi.referer)


class friend_remove:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        return render.friend_remove(utils.me, user)

    def POST(self, user_id):
        wi = web.input()
        body = {'id': user_id, 'mode': 'lite'}
        utils.client.friendships.destroy(body)
        utils.refresh_cache('users_profile', user_id)
        session.action = u'已将 %s 从关注的人中删除。' % wi.name
        raise web.seeother(wi.referer)


class friends:
    def GET(self, user_id=None, page=1):
        user_id = user_id or utils.me['id']
        body = {'id': user_id, 'mode': 'lite', 'count': 50, 'page': page}
        user = utils.users_show({'id': user_id})
        data = utils.client.users.friends(body).json() if user['visible'] else []
        return render.friends(utils.me, user, data, int(page), utils.notice)


class followers:
    def GET(self, user_id=None, page=1):
        user_id = user_id or utils.me['id']
        body = {'id': user_id, 'mode': 'lite', 'count': 50, 'page': page}
        user = utils.users_show({'id': user_id})
        data = utils.client.users.followers(body).json() if user['visible'] else []
        return render.followers(utils.me, user, data, int(page), utils.notice)


class mentions:
    def GET(self, page=1):
        body = {'page': page, 'format': 'html', 'mode': 'lite', 'count': 15}
        data = utils.client.statuses.mentions(body).json()
        utils.cache(data, 'users,statuses')
        return render.mentions(utils.me, data, int(page), utils.notice)


class privatemsg_viewreply:
    def GET(self, msg_id):
        body = {'id': msg_id, 'count': 30, 'mode': 'lite'}
        return render.privatemsg_viewreply(utils.me, utils.privatemsg_show(body), utils.notice)


class privatemsg:
    def GET(self, page=1):
        body = {'page': page, 'format': 'html', 'mode': 'lite', 'count': 10}
        data = utils.client.direct_messages.inbox(body).json()
        utils.cache(data, 'privatemsg')
        return render.privatemsg(utils.me, data, int(page), utils.notice)


class privatemsg_sent:
    def GET(self, page=1):
        body = {'page': page, 'format': 'html', 'mode': 'lite', 'count': 10}
        data = utils.client.direct_messages.sent(body).json()
        utils.cache(data, 'privatemsg')
        return render.privatemsg_sent(utils.me, data, int(page), utils.notice)


class privatemsg_reply:
    def GET(self, msg_id):
        body = {'id': msg_id, 'count': 30, 'mode': 'lite'}
        raw_dm = utils.privatemsg_show(body)
        return render.privatemsg_reply(utils.me, raw_dm)

    def POST(self, msg_id):
        wi = web.input()
        body = {'user': wi.sendto, 'text': wi.content, 'in_reply_to_id': msg_id}
        try:
            utils.client.direct_messages.new(body)
            session.action = '私信发送成功！'
        except:
            session.action = '很抱歉，只有你是 Ta 的好友才能通过 API 发送私信'
        raise web.seeother('/privatemsg')


class privatemsg_create:
    def GET(self, user_id):
        user = utils.users_show({'id': user_id})
        referer = web.ctx.env.get('HTTP_REFERER', '/home').replace(web.ctx.home, '')
        return render.privatemsg_create(utils.me, user, referer, utils.notice)

    def POST(self, msg_id):
        wi = web.input()
        body = {'user': wi.sendto, 'text': wi.content}
        try:
            utils.client.direct_messages.new(body)
            session.action = '私信发送成功！'
        except:
            session.action = '很抱歉，只有你是 Ta 的好友才能通过API发送私信'
        raise web.seeother(wi.referer)


class privatemsg_del:
    def GET(self, msg_id):
        referer = web.ctx.env.get('HTTP_REFERER', '/home')
        referer = '/privatemsg/sent' if 'sent' in referer else '/privatemsg'
        return render.privatemsg_del(utils.me, msg_id, referer)

    def POST(self, msg_id):
        wi = web.input()
        body = {'id': msg_id}
        utils.client.direct_messages.destroy(body)
        session.action = '私信删除成功！'
        raise web.seeother(wi.referer)


class statuses:
    def GET(self, msg_id):
        body = {'id': msg_id, 'mode': 'lite', 'format': 'html'}
        data = utils.msg_show(body, raw=True)
        if data:
            return render.statuses(utils.me, data, utils.notice)
        else:
            user = session.users.get(msg_id)
            if session.http == 'HTTP Error 403: Forbidden':
                return render.statuses_lock(utils.me, user, utils.notice)
            elif session.http == 'HTTP Error 404: Not Found':
                return render.statuses_del(utils.me, user, utils.notice)


class browse:
    def GET(self):
        body = {'count': 15, 'format': 'html'}
        data = utils.client.statuses.public_timeline(body).json()
        utils.cache(data, 'users,statuses')
        return render.browse(utils.me, data, utils.notice)


class album:
    def GET(self, user_id, page=1):
        user_id = user_id or utils.me['id']
        body = {'id': user_id, 'count': 10, 'mode': 'lite', 'page': int(page)}
        user = utils.users_show({'id': user_id})
        data = utils.album(body) if user['visible'] else []
        return render.album(utils.me, user, data, int(page), utils.notice)


class photo:
    def GET(self, mode, msg_id):
        body = {'id': msg_id, 'mode': 'lite', 'format': 'html'}
        data = utils.msg_show(body, raw=True)
        user_id = session.users.get(msg_id)['id']
        if data:
            idx, nav = utils.photo_navigate(msg_id)
            user = utils.users_show({'id': user_id})
            return render.photo(utils.me, user, data, idx, nav, mode, utils.notice)
        else:
            user = session.users.get(msg_id)
            if session.http == 'HTTP Error 403: Forbidden':
                return render.photo_403(utils.me, user, utils.notice)
            elif session.http == 'HTTP Error 404: Not Found':
                return render.photo_404(utils.me, user, utils.notice)


class photo_upload:
    def GET(self):
        return render.photo_upload(utils.me, utils.notice)

    def POST(self):
        wi = web.input(photo={})
        if wi.get('desc') == session.get('last'):
            session.action = '请勿发重复消息！'
            raise web.seeother('/photo.upload')
        if not wi.photo.filename:
            session.action = '请选择文件！'
            raise web.seeother('/photo.upload')
        file_type = mimetypes.guess_type(wi.photo.filename)[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png', 'image/x-png']:
            session.action = '照片格式错误'
            raise web.seeother('/photo.upload')
        desc = wi.get('desc') or u'上传了新照片'
        args = {'photo': wi.photo.filename, 'status': desc}
        body, headers = fanfou.pack_image(args, binary=wi.photo.file.read())
        utils.client.photos.upload(body, headers)
        session.last = desc
        session.action = '发送成功！'
        raise web.seeother('/home')


class photo_del:
    def GET(self, msg_id):
        return render.photo_del(utils.me, msg_id)

    def POST(self, msg_id):
        utils.client.statuses.destroy({'id': msg_id})
        session.action = '照片删除成功！'
        raise web.seeother('/album')


class search:
    def GET(self):
        wi = web.input(p=1)
        if not wi.get('q'):
            return render.search(utils.me, wi, (), utils.notice)
        elif wi.get('st', '0') == '0':    # public timeline
            m = 'since_id' if wi.get('t') == '0' else 'max_id'
            body = {
                'q': wi.q, 'format': 'html', 'count': 10,
                'mode': 'lite', m: wi.get('m', '')
            }
            data = utils.client.search.public_timeline(body).json()
            utils.cache(data, 'users,statuses')
            if body.get('since_id'):
                wi.more = True
            elif len(data) >= 10:
                body['max_id'] = data[-1]['id']
                wi.more = bool(utils.client.search.public_timeline(body).json())
            else:
                wi.more = False
            return render.search(utils.me, wi, data, utils.notice)
        elif wi.get('st') == '1':    # my timeline
            m = 'since_id' if wi.get('t') == '0' else 'max_id'
            body = {
                'q': wi.q, 'format': 'html', 'count': 10,
                'mode': 'lite', m: wi.get('m', '')
            }
            data = utils.client.search.user_timeline(body).json()
            utils.cache(data, 'users,statuses')
            if body.get('since_id'):
                wi.more = True
            elif len(data) >= 10:
                body['max_id'] = data[-1]['id']
                wi.more = bool(utils.client.search.user_timeline(body).json())
            else:
                wi.more = False
            return render.search(utils.me, wi, data, utils.notice)
        elif wi.get('st') == '2':    # search users
            body = {
                'q': wi.q, 'format': 'html', 'count': 10,
                'mode': 'lite', 'page': int(wi.p)
            }
            data = utils.client.search.users(body).json()
            data = data or {'total_number': 0, 'users': []}
            if len(data['users']) >= 10:
                body['page'] += 1
                wi.more = bool(utils.client.search.users(body).json())
            else:
                wi.more = False
            return render.find(utils.me, wi, data, utils.notice)


class query:
    def GET(self, word):
        body = {'q': word.replace('+', ' '), 'format': 'html', 'count': 10, 'mode': 'lite'}
        data = utils.client.search.public_timeline(body).json()
        utils.cache(data, 'users,statuses')
        if len(data) >= 10:
            body['max_id'] = data[-1]['id']
            body['more'] = bool(utils.client.search.public_timeline(body).json())
        else:
            body['more'] = False
        return render.q(utils.me, body, data, utils.notice)


class space:
    def GET(self, user_id, page=1):
        if int(page) == 1:
            utils.refresh_cache('users_profile', user_id)
        user = utils.users_show({'id': user_id})
        if user['visible']:
            body = {'id': user_id, 'page': page, 'format': 'html', 'mode': 'lite', 'count': 15}
            data = utils.client.statuses.user_timeline(body).json()
            utils.cache(data, 'users,statuses')
            return render.space(utils.me, user, data, int(page), utils.notice)
        else:
            return render.space_lock(utils.me, user, utils.notice)


class userview:
    def GET(self, user_id, page=1):
        user = utils.users_show({'id': user_id})
        if user['visible']:
            body = {'id': user_id, 'page': page, 'format': 'html', 'mode': 'lite', 'count': 15}
            data = utils.client.statuses.home_timeline(body).json()
            utils.cache(data, 'users,statuses')
            return render.userview(utils.me, user, data, int(page), utils.notice)
        else:
            return render.space_lock(utils.me, user, utils.notice)


class dialogue:
    def GET(self, user_id, page=1):
        user = utils.users_show({'id': user_id})
        if user['visible']:
            body = {'id': user_id, 'page': page, 'format': 'html', 'mode': 'lite', 'count': 15}
            data = utils.client.direct_messages.conversation(body).json()
            utils.cache(data, 'privatemsg')
            return render.dialogue(utils.me, user, data, int(page), utils.notice)
        else:
            return render.space_lock(utils.me, user, utils.notice)


class settings:
    def GET(self):
        utils.refresh_cache('me,conf')
        utils.refresh_cache('users_profile', utils.me['id'])
        user = utils.users_show({'id': utils.me['id']})
        blacklist = ';'.join(utils.blacklist())
        return render.settings(utils.me, user, blacklist, utils.tail(), utils.notice)

    def POST(self):
        wi = web.input(image={})
        body = {'name': wi.name, 'description': wi.bio or '\n'}
        utils.client.account.update_profile(body)

        if wi.image.filename:
            file_type = mimetypes.guess_type(wi.image.filename)[0]
            if file_type not in ['image/gif', 'image/jpeg', 'image/png', 'image/x-png']:
                session.action = '图片格式错误'
                raise web.seeother('/settings')
            args = {'image': wi.image.filename}
            body, headers = fanfou.pack_image(args, binary=wi.image.file.read())
            utils.client.account.update_profile_image(body, headers)

        if wi.blacklist:
            models.conf.set(utils.me['id'], wi.blacklist.split(';'))

        user = utils.users_show({'id': utils.me['id']})
        session.action = '保存成功！'
        return render.settings(utils.me, user, wi.blacklist, utils.tail(), utils.notice)


class share_confirm:
    def GET(self):
        cid = utils.gen_uuid(session.consumer)
        raise web.seeother('/share?cid=%s' % cid)


class share:
    def GET(self):
        referer = web.ctx.env.get('HTTP_REFERER', '')
        http_host = web.ctx.env.get('HTTP_HOST')
        cid = web.input().get('cid').strip('/')
        if http_host in referer:
            http_code = 200
        else:
            data = models.consumer.get(cid)
            try:
                consumer = data['consumer']
                callback = 'http://%s/callback' % http_host
                client = fanfou.OAuth(consumer, callback=callback)
                session.consumer = consumer
                session.request_token = client.request_token()
                raise web.seeother(client.authorize_url)
            except urllib2.HTTPError:
                http_code = 404 if data else 403
        return render.share(cid, http_code, http_host)


class autologin_confirm:
    def GET(self):
        sid = web.cookies().get('sid')
        raise web.seeother('/autologin?sid=%s' % sid)


class autologin:
    def GET(self):
        referer = web.ctx.env.get('HTTP_REFERER', '')
        http_host = web.ctx.env.get('HTTP_HOST')
        if http_host in referer:
            return render.autologin()
        else:
            session.kill()
            sid = web.input().get('sid').strip('/')
            data = models.token.get(sid)
            try:
                utils.token_verify(data)     # Verify the token
                web.setcookie('sid', sid, 2592000)
            except:
                web.setcookie('sid', '', 2592000)
                return render.authorize('书签登录失败，请重新验证。')
            raise web.seeother('/home')


class logout:
    def GET(self):
        session.kill()
        web.setcookie('sid', '', 2592000)
        return render.authorize('你已经安全退出。')


class authorize:
    def GET(self):
        sid = web.cookies().get('sid')
        if web.input().get('m'):
            session.kill()
            web.setcookie('sid', '', 2592000)
            return render.authorize_d(None)
        if sid:
            data = models.token.get(sid)
            try:
                utils.token_verify(data)
            except:
                return render.authorize('Token 已失效，请重新认证。')
            raise web.seeother('/home')
        else:
            return render.authorize(None)

    def POST(self):
        wi = web.input()
        http_host = web.ctx.env.get('HTTP_HOST')
        callback = 'http://%s/callback' % http_host
        if wi.get('user-defined'):
            consumer = {'key': wi.key, 'secret': wi.secret}    # from authorize_d.html
        else:
            consumer = models.consumer.get(wi.cid)['consumer']    # from authorize.html
        try:
            client = fanfou.OAuth(consumer, callback=callback)
            session.consumer = consumer
            session.request_token = client.request_token()
        except:
            return render.authorize_d('请填写正确的 Consumer。')
        raise web.seeother(client.authorize_url)


class callback:
    def GET(self):
        consumer = session.consumer
        request_token = session.request_token
        if request_token:
            client = fanfou.OAuth(consumer, request_token)
            token = client.access_token()
            cid = utils.gen_uuid(consumer)
            sid = utils.gen_uuid(token)
            models.consumer.set(cid, utils.fetch_tail(consumer), consumer)
            models.token.set(sid, cid, token)
            session.token = token
            session.request_token = None
            web.setcookie('sid', sid, 2592000)
            raise web.seeother('/home')
        else:
            raise web.seeother('/authorize')


class help:
    def GET(self):
        topic = web.input().get('topic')
        try:
            return web.template.frender('templates/help_%s.html' % topic, globals=globals())()
        except:
            return web.template.frender('templates/help_notfound.html', globals=globals())()


web.config.debug = True
app = web.application(urls.urls, globals())

session = web.session.Session(app, models.session)
app.notfound = utils.notfound
app.internalerror = utils.internalerror
app.add_processor(web.loadhook(utils.authorize))
render = web.template.render(os.path.join(curdir, 'templates'), globals=globals())

if __name__ == '__main__':
    app.run()
