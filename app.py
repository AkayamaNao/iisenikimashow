# # -*- coding: utf-8 -*-
from flask import request, abort, Flask
from sqlalchemy import create_engine, func
import pandas as pd
from sqlalchemy.orm import sessionmaker
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
import requests
import json
import random, string

import settings
from models import *

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
db_engine = create_engine(settings.db_info, pool_pre_ping=True)
line_bot_api = LineBotApi(settings.access_token)
handler = WebhookHandler(settings.secret_key)
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + settings.access_token
}
reply_url = 'https://api.line.me/v2/bot/message/reply'

with app.app_context():
    db.init_app(app)
    # db.drop_all()  # Remove on release
    db.create_all()


def gene_id(s):
    while True:
        id = '@' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])
        user = s.query(Users).filter_by(room=id).first()
        if user is None:
            return id


def isfloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def quiz_results(s, room_id):
    query = f'''
        select answers.id,answers.user_id,users.name,answers.number,answers.status from answers right outer join (select * from users where room='{room_id}') as users on answers.user_id = users.id;
        '''
    df = pd.read_sql(query, db_engine)
    if df['status'].isna().all():
        return 'まだ回答を受け付けていません。誰かが数字を送信するとゲームが始まります。'
    elif df['status'].isna().any():
        df['text'] = '回答待ち'
        df.loc[df['status'] == 1, 'text'] = '回答済'
        text = '【回答受付中】'
        for index, row in df.iterrows():
            text += f"\n{row['name']}\t\t{row['text']}"
        return text

    if df['status'].all():
        for index, row in df.iterrows():
            answer = s.query(Answers).filter_by(id=row['id']).first()
            answer.status = 0
        s.commit()
    elif df['status'].any():
        df['text'] = '回答待ち'
        df.loc[df['status'] == 1, 'text'] = '回答済'
        text = '【回答受付中】'
        for index, row in df.iterrows():
            text += f"\n{row['name']}\t\t{row['text']}"
        return text
    df = df.sort_values('number')
    df = df.reset_index(drop=True)
    middle = len(df) // 2
    text = '【結果発表】'
    for index, row in df.iterrows():
        number = float(row['number'])
        if number % 1 == 0:
            number = int(number)
        text += f"\n{row['name']}\t\t{number}"
        if index == middle:
            text += '\t☆'
    return text


@app.route('/')
def index():
    return 'hello, world2'


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name
    text = event.message.text

    Session = sessionmaker(bind=db_engine)
    s = Session()
    user = s.query(Users).filter_by(id=user_id).first()
    if user:
        room_id = user.room
        user.name = user_name
    else:
        s.add(Users(id=user_id, name=user_name))
        s.commit()
        room_id = None

    reply_json = []
    if text == '部屋を作る':
        room_id = gene_id(s)
        user.room = room_id
        s.commit()
        reply_json.append({
            "type": "text",
            "text": "新しい部屋を作りました。\n一緒に遊ぶ友達に下記の部屋IDを教えてゲームを始めよう！"
        })
        reply_json.append({
            "type": "text",
            "text": room_id
        })
        line_bot_api.link_rich_menu_to_user(user_id, settings.with_room_id)
    elif text == '部屋に入る':
        reply_json.append({
            "type": "text",
            "text": "一緒に遊ぶ友達に部屋IDを教えてもらってこのトークルームに部屋IDを送信するとその部屋に入ることができます。"
        })
    elif text == '退出する':
        user.room = None
        answer = s.query(Answers).filter_by(user_id=user_id).first()
        if answer:
            s.delete(answer)
        s.commit()
        reply_json.append({
            "type": "text",
            "text": "退出しました。"
        })
        line_bot_api.link_rich_menu_to_user(user_id, settings.none_room_id)
    elif text == '問題を出す':
        if room_id:
            quiz = s.query(Quiz).order_by(func.random()).first()
            reply_json.append({
                "type": "text",
                "text": quiz.text
            })
        else:
            reply_json.append({
                "type": "text",
                "text": "部屋IDを送信してください。"
            })
    elif text == '結果発表':
        if room_id:
            reply_json.append({
                "type": "text",
                "text": quiz_results(s, room_id)
            })
        else:
            reply_json.append({
                "type": "text",
                "text": "部屋IDを送信してください。"
            })
    elif text[0] == '@':
        room_user = s.query(Users).filter_by(room=text).first()
        if room_user:
            user.room = text
            s.commit()
            query = f"select name from users where room='{text}';"
            df = pd.read_sql(query, db_engine)
            member = '\n'.join(df['name'].to_list())
            reply_json.append({
                "type": "text",
                "text": f"部屋に入りました。現在この部屋には\n\n{member}\n\nがいます。"
            })
            reply_json.append({
                "type": "text",
                "text": f"誰かが数字を送信するとゲームが始まります。\n全員が回答を終えると最後に答えた人に結果が表示されます。"
            })
            line_bot_api.link_rich_menu_to_user(user_id, settings.with_room_id)
        else:
            reply_json.append({
                "type": "text",
                "text": f"部屋IDが違います。"
            })
    else:
        if room_id:
            if text.replace('.', '', 1).isdecimal():
                number = float(text)
                if number % 1 == 0:
                    number = int(number)
                query = f'''
                    select answers.id,answers.status from answers right outer join (select * from users where room='{room_id}') as users on answers.user_id = users.id;
                    '''
                df = pd.read_sql(query, db_engine)
                if df['status'].sum() == 0 and ~df['status'].isna().any():
                    for index, row in df.iterrows():
                        answer = s.query(Answers).filter_by(id=int(row['id'])).first()
                        s.delete(answer)
                answer = s.query(Answers).filter_by(user_id=user_id, status=1).first()
                if answer:
                    s.delete(answer)
                s.add(Answers(user_id=user_id, number=number))
                s.commit()
                reply_json.append({
                    "type": "text",
                    "text": f"{number} の回答を受け付けました。"
                })
                reply_json.append({
                    "type": "text",
                    "text": quiz_results(s, room_id)
                })
            else:
                reply_json.append({
                    "type": "text",
                    "text": "数字のみを送信してください。"
                })
        else:
            reply_json.append({
                "type": "text",
                "text": "部屋IDを送信してください。"
            })

    data = {'replyToken': event.reply_token, 'messages': reply_json}
    res = requests.post(reply_url, data=json.dumps(data), headers=headers)


if __name__ == '__main__':
    app.run()

# s.add(Quiz(text="納豆が一番おいしく感じるのは、何回混ぜた時？"))
# s.commit()
