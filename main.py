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
import os

import jinja2
import webapp2

from google.appengine.ext import ndb

import getimageinfo

#jinjaの定義
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Omoide(ndb.Model):
    """画像のモデル。"""
    user = ndb.StringProperty()
    image = ndb.BlobProperty()
    comment = ndb.StringProperty()
    mimetype = ndb.StringProperty()
    date = ndb.DateProperty()

    
class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.redirect('./list')

class ImageHandler(webapp2.RequestHandler):
    """画像を出力する"""
    def get(self, urlsafe_key):
        omoide = ndb.Key(urlsafe=urlsafe_key).get()
        if omoide:
            self.response.headers['Content-Type'] = str(omoide.mimetype)
            self.response.out.write(omoide.image)
        else:
            self.error(404)
            self.response.out.write('404 not found.')
            self.response.out.write(str(omoide))
        return



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
            view_item[-1][-1].append([omoide.key.urlsafe(), omoide.comment])
        template_value = {'view_item':view_item}
        template = JINJA_ENVIRONMENT.get_template('./html/list.html')
        self.response.write(template.render(template_value))


class RegistHandler(webapp2.RequestHandler):
    """画像を登録する。"""
    def get(self):
        template_value = {'message':u'写真と日付を入力して、登録を押してください。'}
        template = JINJA_ENVIRONMENT.get_template('./html/register.html')
        self.response.write(template.render(template_value))

    def post(self):
        message = ''
        is_good = True

        #正規の画像であるか調べる。
        try:
            image = str(self.request.get('image'))
            content_type, height, width = getimageinfo.getImageInfo(image)
            if content_type == "":
                message = message + u"登録できるファイルは画像だけです。"
                is_good = False
        except:
            message = message + u"登録できるファイルは画像だけです。"
            is_good = False

        #正規の日付であるか調べる。
        try:
            year = int(self.request.get('year'))
            month = int(self.request.get('month'))
            omoide_date = datetime.date(year, month, 1)
        except (TypeError, ValueError):
            message = message + u"日付が有効でありません。"
            is_good = False

        #画像をDBに登録する。
        if is_good:
            omoide = Omoide()
            omoide.user = 'test'
            omoide.image = image
            omoide.comment = self.request.get('comment')
            omoide.mimetype = self.request.body_file.vars['image'].headers['content-type']
            omoide.date = omoide_date
            omoide.put()
            message = message + u"登録しました。"

        #画面を出力
        template_value = {'message':message}
        template = JINJA_ENVIRONMENT.get_template('./html/register.html')
        self.response.write(template.render(template_value))

#ルータ
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/image/([^/]+)', ImageHandler),
    ('/list', ListHandler),
    ('/register', RegistHandler),
], debug=True)
