#!/usr/bin/env python
#!-*- coding:utf-8 -*-
# copyright 2014 hrwatahiki
# mail: hrwatahiki at gmail.com
# twitter:@hrwatahiki
# github:https://github.com/hrwatahiki/omoide-makimono
# This script is under MIT License.

import datetime
import hashlib
import os
import urllib

import jinja2
import webapp2

import logging
import base64

from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from gaesessions import get_current_session

#jinjaの定義
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Omoide(ndb.Model):
    """画像のモデル。"""
    user_name = ndb.StringProperty()
    image_key = ndb.BlobKeyProperty()
    comment = ndb.StringProperty()
    date = ndb.DateProperty()


class User(ndb.Model):
    """ユーザー。"""
    user_name = ndb.StringProperty()
    password = ndb.StringProperty()


def GetListViewItem(user_name):
    """一覧用のリストを作成する。"""
    omoides = Omoide.query(Omoide.user_name == user_name).order(Omoide.date).fetch(1000)
    view_item = []
    date = datetime.date(1, 1, 1)
    for omoide in omoides:
        if date != omoide.date:
            date = omoide.date
            view_item.append([date.year, date.month, []])
        view_item[-1][-1].append([omoide.image_key, omoide.comment])
    return view_item


def Decode(str):
    """base64→utf-8のデコードを行う。"""
    try:
        r = base64.b64decode(str).decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError, TypeError):
        r = str
    except:
        logging.error('Unknown error in Decode.')
        r = str
    return r


class MainHandler(webapp2.RequestHandler):
    """デフォルト。ログイン画面へリダイレクトする。"""
    def get(self):
        self.redirect('/login')
        return


class AboutHandler(webapp2.RequestHandler):
    """サービスの説明を表示する。"""
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('/html/about.html')
        self.response.write(template.render({}))


class DeleteHandler(webapp2.RequestHandler):
    """選択したファイルを削除する。"""
    def get(self, resource):
        session = get_current_session()
        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        key = blob_info.key()
        blob_info.delete()
        Omoide.query(Omoide.image_key == key).get().key.delete()

        self.redirect('/delete_list')
        return


class DeleteListHandler(webapp2.RequestHandler):
    """削除用の一覧を表示する。"""
    def get(self):
        session = get_current_session()
        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        view_item = GetListViewItem(session['user_name'])
        template_value = {'user_name':session['user_name'], 'view_item':view_item}
        template = JINJA_ENVIRONMENT.get_template('/html/delete_list.html')
        self.response.write(template.render(template_value))
        return


class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    """画像を出力する。"""
    def get(self, resource):
        session = get_current_session()
        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)
        return


class ListHandler(webapp2.RequestHandler):
    """一覧を表示する。"""
    def get(self):
        session = get_current_session()
        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        view_item = GetListViewItem(session['user_name'])
        template_value = {'user_name':session['user_name'], 'view_item':view_item}
        template = JINJA_ENVIRONMENT.get_template('/html/list.html')
        self.response.write(template.render(template_value))
        return


class LoginHandler(webapp2.RequestHandler):
    """ログインする。"""
    def get(self):
        template_value = {'message':u'ユーザ名とパスワードを入れて、ログインか新規登録を押してください。'}
        template = JINJA_ENVIRONMENT.get_template('/html/login.html')
        self.response.write(template.render(template_value))
        return

    def post(self):
        #セッションを終了する。
        session = get_current_session()
        if session.is_active():
            session.terminate()
        logged_in = False
        message = u'ログインに失敗しました。'

        user_name = self.request.get('user_name')
        password = hashlib.sha512(self.request.get('password')).hexdigest()

        if self.request.get('login'):
            #DBにユーザ名とパスワードが一致するユーザがあれば、ログインする。
            user = User.query(ndb.AND(User.user_name==user_name, User.password==password)).fetch(1)
            if user:
                logged_in = True
        elif self.request.get('new'):
            #DBに同じユーザがいなければ、ユーザを新規登録し、ログインする。
            user = User.query(ndb.AND(User.user_name==user_name)).fetch(1)
            if user:
                message = u'ユーザ名を変えてください。'
            else:
                user = User()
                user.user_name = user_name
                user.password = password
                user.put()
                logged_in = True

        if logged_in:
            session['user_name'] = user_name
            session['token'] = hashlib.sha512('3rjTK9pJVZtG'+str(datetime.datetime.now())).hexdigest()
            self.redirect('/list')
            return

        template_value = {'message':message}
        template = JINJA_ENVIRONMENT.get_template('/html/login.html')
        self.response.write(template.render(template_value))


class LogoutHandler(webapp2.RequestHandler):
    """ログアウトする。"""
    def get(self):
        #セッションを終了する。
        session = get_current_session()
        session.terminate()

        template_value = {'message':u'ログアウトしました。'}
        template = JINJA_ENVIRONMENT.get_template('/html/login.html')
        self.response.write(template.render(template_value))
        return


class RegistHandler(webapp2.RequestHandler):
    """画像を登録する。"""
    def get(self):
        session = get_current_session()
        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        template_value = {
            'user_name':session['user_name'],
            'message':u'写真と日付を入力して、登録を押してください。',
            'upload_url':blobstore.create_upload_url('/upload'),
            'year':'',
            'month':'',
            'comment':'',
            'token':session['token'],
        }
        template = JINJA_ENVIRONMENT.get_template('/html/register.html')
        self.response.write(template.render(template_value))


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    """画像をBlobStoreに格納する。"""
    def post(self):
        session = get_current_session()
        message = ''
        date_is_good = False
        file_is_good = False
        file_exists = True
        token_is_good = False

        comment = Decode(self.request.get('comment'))

        #正規の日付であるか調べる。
        try:
            year = int(self.request.get('year'))
            month = int(self.request.get('month'))
            omoide_date = datetime.date(year, month, 1)
        except (TypeError, ValueError):
            message = message + u'正しい日付を入力してください。'
        else:
            date_is_good = True

        #正しいファイルがあるか調べる。
        upload_files = self.get_uploads('image')  # 'file' is file upload field in the form
        if upload_files:
            blob_info = upload_files[0]
            if blob_info.content_type.startswith('image'):
                file_is_good = True
            else:
                message = message + u'画像を選択してください。'
        else:
            message = message + u'画像を選択してください。'
            file_exists = False

        #トークンが正しいか調べる。
        if session.has_key('token'):
            if session['token'] == self.request.get('token'):
                token_is_good = True

        #日付が正しく、ファイルが正しく、トークンが正しければ登録する。
        if date_is_good and file_is_good and token_is_good and session.has_key('user_name'):
            omoide = Omoide()
            omoide.user_name = session['user_name']
            omoide.image_key = blob_info.key()
            omoide.comment = comment
            omoide.date = omoide_date
            omoide.put()
            message = message + u'登録しました。'
        #どちらかが間違っている場合は、アップロードしたファイルを削除する。
        elif file_exists:
            blob_info.delete()

        if not session.has_key('user_name'):
            self.redirect('/login')
            return

        #画面を出力する。
        template_value = {
            'user_name':session['user_name'],
            'message':message,
            'upload_url':blobstore.create_upload_url('/upload'),
            'year':self.request.get('year'),
            'month':self.request.get('month'),
            'comment':comment,
            'token':session['token'],
        }
        template = JINJA_ENVIRONMENT.get_template('/html/register.html')
        self.response.write(template.render(template_value))


#ルータ
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/about', AboutHandler),
    ('/delete/([^/]+)', DeleteHandler),
    ('/delete_list', DeleteListHandler),
    ('/download/([^/]+)', DownloadHandler),
    ('/list', ListHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/register', RegistHandler),
    ('/upload', UploadHandler),
], debug=True)
