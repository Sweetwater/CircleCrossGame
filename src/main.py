# -*- coding: utf-8 -*-

import os
import logging
from google.appengine.api import channel, users
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from django.utils import simplejson

# ユーザデータ
class UserData(db.Model):
    user = db.UserProperty(required=True)
    addtime = db.DateTimeProperty(auto_now_add=True)

# 試合データ
class MatchData(db.Model):
    status = db.StringProperty(choices=['start','p1_turn','p2_turn','end'], default='start')
    player1 = db.ReferenceProperty(UserData, collection_name='1player')
    player2 = db.ReferenceProperty(UserData, collection_name='2player')
    board = db.ListProperty(long, default=[0,0,0, 0,0,0, 0,0,0])

def PlayerPageGet(self, playerId):
    # ユーザがログインしているか調べる
    user = users.get_current_user()
    # ユーザがログインしている場合
    if user:
        # ユーザデータを取得または挿入
        keyname = "key:" + user.nickname()
        userData = UserData.get_or_insert(keyname, user=user)

        # 試合データの初期化
        matchName = 'firstMatch'
        matchData = MatchData.get_or_insert(matchName)
        matchData.status = 'p1_turn'

        # 試合データにユーザを追加
        if playerId == 'p1':
            matchData.player1 = userData
            logging.log(25, "set matchData.player1 :" + matchData.player1.user.nickname())
        if playerId == 'p2':
            matchData.player2 = userData
            logging.log(25, "set matchData.player2 :" + matchData.player2.user.nickname())
        matchData.put()

        # チャネルを生成
        id = channel.create_channel(userData.user.nickname())

        # チャネルIDをクライアントに渡す
        template_values = {'channel_id': id,
                           'player_id': playerId,
                           'status': matchData.status}
        path = os.path.join(os.path.dirname(__file__), 'views', 'player.html')
        html = template.render(path, template_values)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(html)
    # ユーザがログインしていない場合
    else:
        # ログインページに飛ばす
        self.redirect(users.create_login_url(self.request.uri))

def PlayerPagePost(self, playerId):
    # どこに置いたかの情報をもらう
    putIndex = self.request.get('putIndex')
    logging.log(25, "post " + playerId  + " putIndex: " + putIndex)

    # 試合データを更新
    matchData = MatchData.get_by_key_name('firstMatch')
    matchData.board[int(putIndex)] = {'p1':1,'p2':2}[playerId]
    matchData.status = {'p1':'p2_turn', 'p2':'p1_turn'}[playerId]
    matchData.put()

    # 送信メッセージを作成
    messageData = {
        'status':matchData.status,
        'putPlayer':playerId,
        'putIndex':putIndex
    }
    message = simplejson.dumps(messageData)
    logging.log(25, "send message :" + message)

    # メッセージの送信
    if playerId == 'p1' and matchData.player2:
        messageId = matchData.player2.user.nickname()
        channel.send_message(messageId, message)
        logging.log(25, "send :" + matchData.player2.user.nickname())
    if playerId == 'p2' and matchData.player1:
        messageId = matchData.player1.user.nickname()
        channel.send_message(messageId, message)
        logging.log(25, "send :" + matchData.player1.user.nickname())

    self.response.out.write(message)


class Player1Page(webapp.RequestHandler):
    def get(self):
        PlayerPageGet(self, 'p1')

    def post(self):
        PlayerPagePost(self, 'p1')

class Player2Page(webapp.RequestHandler):
    def get(self):
        PlayerPageGet(self, 'p2')

    def post(self):
        PlayerPagePost(self, 'p2')

application = webapp.WSGIApplication([('/player1', Player1Page),
                                      ('/player2', Player2Page)],
                                      debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
