#!/usr/bin/env python
#!-*- coding:utf-8 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import urllib
import os

import jinja2
import webapp2

from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import getimageinfo


#jinjaの定義
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Omoide(ndb.Model):
    """画像のモデル。"""
    user = ndb.StringProperty()
    image_key = ndb.BlobKeyProperty()
    comment = ndb.StringProperty()
    date = ndb.DateProperty()


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.redirect('/list')


class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    """画像を出力する。"""
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)


class ListHandler(webapp2.RequestHandler):
    """一覧を表示する。"""
    def get(self):
        omoides = Omoide.query(Omoide.user == 'test').order(Omoide.date).fetch(100)
        view_item = []
        date = datetime.date(1, 1, 1)
        for omoide in omoides:
            if date != omoide.date:
                date = omoide.date
                view_item.append([date.year, date.month, []])
            view_item[-1][-1].append([omoide.image_key, omoide.comment])
        template_value = {'view_item':view_item}
        template = JINJA_ENVIRONMENT.get_template('/html/list.html')
        self.response.write(template.render(template_value))


class RegistHandler(webapp2.RequestHandler):
    """画像を登録する。"""
    def get(self):
        template_value = {
            'message':u'写真と日付を入力して、登録を押してください。',
            'upload_url':blobstore.create_upload_url('/upload'),
            'year':'',
            'month':'',
            'comment':'',
        }
        template = JINJA_ENVIRONMENT.get_template('/html/register.html')
        self.response.write(template.render(template_value))


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    """画像をBlobStoreに格納する。"""
    def post(self):
        message = ''
        date_is_good = True
        file_is_good = True
        file_exists = True
        #正規の日付であるか調べる。
        try:
            year = int(self.request.get('year'))
            month = int(self.request.get('month'))
            omoide_date = datetime.date(year, month, 1)
        except (TypeError, ValueError):
            message = message + u'正しい日付を入力してください。'
            date_is_good = False

        #正しいファイルがあるか調べる。
        upload_files = self.get_uploads('image')  # 'file' is file upload field in the form
        if upload_files:
            blob_info = upload_files[0]
            if not blob_info.content_type.startswith('image'):
                message = message + u'画像を選択してください。'
                file_is_good = False
        else:
            message = message + u'画像を選択してください。'
            date_is_good = False
            file_is_good = False
            file_exists = False

        if date_is_good and file_is_good:
            omoide = Omoide()
            omoide.user = 'test'
            omoide.image_key = blob_info.key()
            omoide.comment = self.request.get('comment')
            omoide.date = omoide_date
            omoide.put()
            message = message + u'登録しました。'
        elif file_is_good:
            blob_info.delete()


        #画面を出力
        template_value = {
            'message':message,
            'upload_url':blobstore.create_upload_url('/upload'),
            'year':self.request.get('year'),
            'month':self.request.get('month'),
            'comment':self.request.get('comment'),
        }
        template = JINJA_ENVIRONMENT.get_template('/html/register.html')
        self.response.write(template.render(template_value))


#ルータ
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/download/([^/]+)', DownloadHandler),
    ('/list', ListHandler),
    ('/register', RegistHandler),
    ('/upload', UploadHandler),
], debug=True)
