import requests, time, re, pymysql, traceback, json, datetime, random

db = pymysql.connect(host='localhost', user='root', database='little_heart', autocommit=True, unix_socket='/var/run/mysqld/mysqld.sock')
cursor = db.cursor()
s = requests.Session()
zero_timestamp = time.mktime(datetime.date.today().timetuple())
sessions = {}
bot = {}
headers = {}
talking = True
talk_num = 0


class ApiException(Exception):
    def __init__(self):
        return

    def __str__(self):
        return


def printer(info, *args):
    now = int(time.time())
    format_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    content = f'[{format_time}] {info} {" ".join(f"{str(arg)}" for arg in args)}'
    print(content)


def get_csrf(cookie):
    temp = re.search(r"bili_jct=(.{32})", cookie)
    csrf = str(temp.group(1))
    return csrf


def get_sessions():
    cursor.execute('SELECT * FROM sessions_info')
    results = cursor.fetchall()
    for row in results:
        uid = row[0]
        cursor.execute(f'SELECT config_num FROM clients_info WHERE uid={uid}')
        res = cursor.fetchone()
        config_num = res[0] if res is not None else 0
        sessions[uid] = {
            'timestamp': row[1],
            'cookie': '',
            'send_timestamp': '0',
            'config_num': config_num
        }


def update_sessions():
    cursor.execute('SELECT * FROM sessions_info')
    results = cursor.fetchall()
    for row in results:
        uid = row[0]
        cursor.execute(f'SELECT config_num FROM clients_info WHERE uid={uid}')
        res = cursor.fetchone()
        config_num = res[0] if res is not None else 0
        sessions[uid]['config_num'] = config_num
        sessions[uid]['timestamp'] = row[1]


def get_bot():
    cursor.execute('SELECT * FROM bot_info')
    row = cursor.fetchone()
    bot['uid'] = row[0]
    bot['cookie'] = row[1]
    bot['dev_id'] = row[2]


def send_config(uid):
    global talk_num
    global talking

    timestamp = int(time.time())
    if sessions[uid]['config_num'] >= 5 or timestamp - int(sessions[uid]['send_timestamp']) < 60:
        return

    payload = {
        'msg[sender_uid]': bot['uid'],
        'msg[receiver_id]': uid,
        'msg[receiver_type]': 1,
        'msg[msg_type]': 1,
        'msg[dev_id]': bot['dev_id'],
        'msg[timestamp]': timestamp,
        'msg[content]': '',
        'csrf': get_csrf(bot['cookie']),
    }
    cursor.execute(f'SELECT * FROM clients_info where uid={uid}')
    row = cursor.fetchone()
    cookie = '无' if row[1] is None else '有'
    auto_gift = '关闭' if row[2] == 0 else '开启'
    completed = '未完成' if row[3] == 0 else '已完成'
    target_name = row[6]

    cookie_status = row[7]
    if cookie == '无':
        cookie_status = ''
    elif cookie_status == 0:
        cookie_status = '，cookie还未被使用过'
    elif cookie_status == 1:
        cookie_status = '，上次使用时cookie还有效'
    elif cookie_status == -1:
        cookie_status = '，错误或已过期的cookie'

    medal_status = row[8]
    if medal_status == 0:
        medal_status = '正常'
    elif medal_status == -1:
        medal_status = '没有粉丝牌'
    elif medal_status == -2:
        medal_status = '粉丝牌对应的主播都未开通直播间'

    msg = '' \
          f'cookie状态：{cookie}{cookie_status}\n' \
          f'自动送礼状态：{auto_gift}\n' \
          f'自送送礼目标：{target_name}\n' \
          f'粉丝牌状态：{medal_status}\n' \
          f'今日小心心任务{completed}\n\n' \
          f'弹幕状态：\n'

    cursor.execute(f'SELECT * FROM messages_info WHERE uid ={uid}')
    rows = cursor.fetchall()
    for row in rows:
        target_id = row[2]
        name = row[3]
        content = row[5]

        msg_status = '未发送'
        if row[6] == 1:
            msg_status = '已发送'
        elif row[6] == -1:
            msg_status = '含有屏蔽词'
        elif row[6] == -2:
            msg_status = '无法发送，可能是UL等级或粉丝牌等级低于直播间屏蔽等级'
        elif row[6] == -3:
            msg_status = '无法发送，因为cookie错误或已过期'
        elif row[6] == -4:
            msg_status = f'无法发送，因为 {name} 未开通直播间'
        msg += f'{target_id}({name})："{content}" —— {msg_status}\n'

    payload['msg[content]'] = json.dumps({'content': msg})

    res = s.post('https://api.vc.bilibili.com/web_im/v1/web_im/send_msg', headers=headers, params=payload).json()

    if res['code'] != 0:
        printer('私信发送失败')
        if res['code'] == 21024:
            printer(res)
        else:
            printer(f'今日私信发送数量达到了最大限制，共发了 {talk_num} 条')
            talk_num = 0
            talking = False
        return

    talk_num += 1
    sessions[uid]['send_timestamp'] = str(timestamp)
    sessions[uid]['config_num'] += 1
    cursor.execute(f'UPDATE clients_info SET config_num={sessions[uid]["config_num"]} WHERE uid={uid};')


def do_command(uid, command, parameter):
    cursor.execute(f'SELECT * FROM clients_info where uid={uid}')
    result = cursor.fetchall()
    if not result:  # 如果为空
        cursor.execute(f'INSERT INTO clients_info(uid) VALUES({uid})')

    if command == '/cookie_commit':
        if (sessions[uid]['cookie']) != '':
            sessions[uid]['cookie'] = sessions[uid]['cookie'].replace('\n', '')
            cursor.execute(f'UPDATE clients_info SET cookie=%s,cookie_status=0 WHERE uid={uid}',
                           [sessions[uid]["cookie"]])
            cursor.execute(f'UPDATE messages_info SET msg_status = 0 WHERE uid ={uid}')
            sessions[uid]['cookie'] = ''

    elif command == '/cookie_clear':
        sessions[uid]['cookie'] = ''

    elif command == '/cookie_append':
        if parameter is not None:
            sessions[uid]['cookie'] += parameter
        if len(sessions[uid]['cookie']) >= 2000:
            sessions[uid]['cookie'] = ''

    elif command == '/config':
        if talking:
            send_config(uid)

    elif command == '/auto_gift':
        if parameter == '0':
            cursor.execute(f'UPDATE clients_info SET auto_gift=0 WHERE uid={uid}')
        elif parameter == '1':
            cursor.execute(f'UPDATE clients_info SET auto_gift=1 WHERE uid={uid}')

    elif command == '/delete':
        cursor.execute(f'SELECT config_num FROM clients_info WHERE uid={uid}')
        [config_num] = cursor.fetchone()
        cursor.execute(f'DELETE FROM clients_info WHERE uid={uid}')
        cursor.execute(f'INSERT INTO clients_info(uid,config_num) VALUES({uid},{config_num})')
        cursor.execute(f'DELETE FROM messages_info WHERE uid={uid}')
        sessions[uid]['cookie'] = ''

    elif command == '/target':
        if parameter.isdigit():
            target_id = parameter
            res = s.get(f'http://api.bilibili.com/x/space/acc/info?mid={target_id}').json()
            if res['code'] == -400:
                return
            if res['code'] != 0:
                printer(res)
                printer(f'uid {uid} 获取目标房间号失败')
                raise ApiException()

            room_id = res['data']['live_room']['roomid']
            target_name = res['data']['name']
            cursor.execute(
                f'UPDATE clients_info SET room_id={room_id},target_id={target_id},target_name=%s WHERE uid={uid}',
                target_name)

    elif command == '/message_set':
        arr = parameter.split(' ', 1)
        if len(arr) == 2:
            [target_id, content] = arr
            content = content.strip()

            if len(content) > 20:
                return

            cursor.execute(f'SELECT * FROM messages_info WHERE uid={uid}')
            res = cursor.fetchall()
            if len(res) >= 10:
                return

            res = s.get(f'http://api.bilibili.com/x/space/acc/info?mid={target_id}').json()
            if res['code'] == -400:
                return
            if res['code'] != 0:
                printer(res)
                printer(f'uid {uid} 获取目标房间号失败')
                raise ApiException()

            room_id = res['data']['live_room']['roomid']

            cursor.execute(f'SELECT * FROM messages_info WHERE uid={uid} AND target_id={target_id}')
            if cursor.fetchone() is not None:
                cursor.execute(
                    f'UPDATE messages_info SET content=%s,msg_status=0 WHERE uid={uid} AND target_id={target_id}',
                    content)
            else:
                target_name = res['data']['name']
                cursor.execute(
                    f'INSERT INTO messages_info (uid, target_id, target_name, room_id, content) VALUES({uid}, {target_id}, %s, {room_id}, %s)',
                    [target_name, content])

    elif command == '/message_delete':
        if parameter == 'all':
            cursor.execute(f'DELETE FROM messages_info WHERE uid={uid}')
        elif parameter.isdigit():
            cursor.execute(f'DELETE FROM messages_info WHERE uid={uid} AND target_id={parameter}')


def do_messages(uid, last_timestamp, messages):
    for msg in messages:
        if int(msg['timestamp']) > int(last_timestamp) and msg['sender_uid'] != bot['uid'] and msg['msg_type'] == 1:
            content = json.loads(msg['content'])['content']
            printer(f'{uid}:{content}')
            if content.startswith('/'):
                arr = content.split(' ', 1)
                if len(arr) == 2:
                    [command, parameter] = arr
                    parameter = parameter.strip()
                    do_command(uid, command, parameter)
                else:
                    command = arr[0]
                    do_command(uid, command, None)


def next_day():
    global zero_timestamp, talking, talk_num
    talking = True
    talk_num = 0
    zero_timestamp = time.mktime(datetime.date.today().timetuple())
    cursor.execute('UPDATE clients_info SET completed=0,medal_status=0,config_num=0')
    cursor.execute('UPDATE messages_info SET msg_status=0')


def main():
    res = s.get('https://api.vc.bilibili.com/session_svr/v1/session_svr/get_sessions?session_type=1',
                headers=headers).json()
    if res['code'] != 0:
        printer(res)
        printer('获取session_list失败')
        raise ApiException()

    session_list = res['data']['session_list']
    if session_list is not None:
        for session in session_list:
            uid = session['talker_id']
            timestamp = session['last_msg']['timestamp']

            res = s.get(
                f'https://api.vc.bilibili.com/svr_sync/v1/svr_sync/fetch_session_msgs?talker_id={uid}&session_type=1',
                headers=headers).json()
            if res['code'] != 0:
                printer(res)
                printer('获取session失败')
                raise ApiException()

            messages = res['data']['messages']
            messages.reverse()

            if uid in sessions:
                cursor.execute(f'UPDATE sessions_info set timestamp={timestamp} WHERE uid={uid}')
                last_timestamp = sessions[uid]['timestamp']
                do_messages(uid, last_timestamp, messages)
            else:
                sessions[uid] = {'timestamp': '0', 'cookie': '', 'send_timestamp': '0', 'config_num': 0}
                cursor.execute(f'INSERT INTO sessions_info(uid,timestamp) VALUES({uid},{timestamp})')
                do_messages(uid, 0, messages)

            sessions[uid]['timestamp'] = str(timestamp)


if __name__ == '__main__':
    # next_day()
    get_sessions()
    get_bot()
    headers = {'cookie': bot['cookie']}
    # next_day()

    while True:
        # noinspection PyBroadException
        try:
            if time.time() - zero_timestamp > 87000:
                next_day()

            update_sessions()
            main()
            cursor.execute('UPDATE bot_info SET receive_status=0')
            if talking:
                cursor.execute('UPDATE bot_info SET send_status=0')
            else:
                cursor.execute('UPDATE bot_info SET send_status=-2')

        except ApiException:
            cursor.execute('UPDATE bot_info SET receive_status=-1,send_status=-1')
            for i in range(0, 15):
                printer(f'调用bilibili的API过于频繁，还需冷却 {15 - i} 分钟')
                time.sleep(60)

        except requests.exceptions.ConnectionError as err:
            printer(err)

        except Exception:
            exc = traceback.format_exc()
            printer(exc)

        finally:
            time.sleep(random.randint(5, 10))
