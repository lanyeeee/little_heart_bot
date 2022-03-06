import requests, time, re, pymysql, asyncio, traceback, random

# noinspection PyBroadException
try:
    from urllib import urlencode
except:
    from urllib.parse import urlencode
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

db = pymysql.connect(host='localhost', user='root', database='little_heart', autocommit=True, unix_socket='/var/run/mysqld/mysqld.sock')
cursor = db.cursor()
clients = []
msg_uid = []
s = requests.Session()


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


def get_buvid(cookie):
    temp = re.search(r"LIVE_BUVID=(.*?);", cookie)
    buvid = str(temp.group(1))
    return buvid


def post_e(cookie, room_id, uid):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://live.bilibili.com',
        'Referer': f'https://live.bilibili.com/{room_id}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
        'Cookie': cookie,
    }

    js = s.get(f'https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?&room_id={room_id}').json()

    if js['code'] != 0:
        printer(js)
        printer(f'uid {uid} 获取直播间信息失败')
        raise ApiException()

    room_info = js['data']['room_info']
    parent_area_id = int(room_info['parent_area_id'])
    area_id = int(room_info['area_id'])

    payload = {
        'id': [parent_area_id, area_id, 1, room_id],
        'device': '["AUTO8716422349901853","3E739D10D-174A-10DD5-61028-A5E3625BE56450692infoc"]',  # LIVE_BUVID + _uuid
        'ts': int(time.time()) * 1000,
        'is_patch': 0,
        'heart_beat': [],
        'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
        'csrf_token': get_csrf(cookie),
        'csrf': get_csrf(cookie),
        'visit_id': ''
    }

    data = urlencode(payload)

    response = s.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E', headers=headers,
                      data=data, verify=False).json()

    if response['code'] != 0:
        printer(response)
        printer(f'uid {uid} 发送E心跳包失败')
        raise ApiException()

    payload['ets'] = response['data']['timestamp']
    payload['secret_key'] = response['data']['secret_key']
    payload['heartbeat_interval'] = response['data']['heartbeat_interval']
    payload['secret_rule'] = response['data']['secret_rule']
    return payload


def post_x(cookie, payload, room_id):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://live.bilibili.com',
        'Referer': f'https://live.bilibili.com/{room_id}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
        'Cookie': cookie,
    }
    s_data = {
        "t": {
            'id': payload['id'],
            "device": payload['device'],
            "ets": payload['ets'],
            "benchmark": payload['secret_key'],
            "time": payload['heartbeat_interval'],
            "ts": int(time.time()) * 1000,  # 当前秒
            "ua": payload['ua']
        },
        "r": payload['secret_rule']
    }
    t = s_data['t']
    payload = {
        's': generate_s(s_data),
        'id': t['id'],
        'device': t['device'],
        'ets': t['ets'],
        'benchmark': t['benchmark'],
        'time': t['time'],
        'ts': t['ts'],
        "ua": t['ua'],
        'csrf_token': payload['csrf'],
        'csrf': payload['csrf'],
        'visit_id': '',
    }
    payload = urlencode(payload)

    return s.post('https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X', headers=headers,
                  data=payload, verify=False).json()


def generate_s(data):
    response = s.post('http://localhost:3000/enc', json=data).json()
    return response['s']


def get_clients():
    global clients
    cursor.execute(
        'SELECT * FROM clients_info WHERE completed = 0 AND cookie_status != -1 AND medal_status = 0 LIMIT 10')
    results = cursor.fetchall()

    clients = [{
        'uid': row[0],
        'cookie': row[1],
        'auto_gift': row[2],
        'room_id': row[4],
        'target_id': row[5]
    } for row in results]

    # printer(f'get_clients: clients size = {len(clients)}')


def get_msg_uid():
    global msg_uid
    cursor.execute('SELECT DISTINCT uid FROM messages_info WHERE msg_status = 0 LIMIT 5')
    rows = cursor.fetchall()
    msg_uid = [row[0] for row in rows]


def get_medals():
    global clients
    for client in clients[:]:
        headers = {'cookie': client['cookie']}
        try:
            js = s.get('https://api.bilibili.com/x/web-interface/nav', headers=headers).json()
            if js['code'] == -412:
                printer(js)
                raise ApiException()
            if js['code'] != 0:
                printer(js)
                client_cookie_error(client)
                continue

        except ApiException:
            raise

        except Exception as er:
            printer(er)
            printer(headers)
            client_cookie_error(client)
            continue

        cursor.execute(f'UPDATE clients_info SET cookie_status=1 WHERE uid = {client["uid"]}')
        js = s.get('https://api.live.bilibili.com/i/ajaxGetMyMedalList', headers=headers).json()
        if js['code'] != 0:
            printer(js)
            printer(f'{client["uid"]} 获取粉丝牌列表失败')
            raise ApiException()

        if not js['data']:
            client_medal_without(client)
            continue

        medals = [{
            'target_id': data['target_id'],
            'room_id': 0
        } for data in js['data']]

        i = 0
        client['medals'] = []
        for medal in medals:
            js = s.get(
                f"http://api.live.bilibili.com/live_user/v1/Master/info?uid={medal['target_id']}").json()

            if js['code'] != 0:
                printer(js)
                printer(f'uid {client["uid"]} 获取room_id失败')
                raise ApiException()

            if js['data']['room_id'] == 0:
                continue

            medal['room_id'] = js['data']['room_id']
            client['medals'].append(medal)

            i += 1
            if i == 12:
                break

        if not client['medals']:
            client_medal_error(client)

    clients = clients[:7]
    # printer(f'get_medal: clients size = {len(clients)}')


def get_bag_data(client):
    headers = {'cookie': client['cookie']}
    return s.get('https://api.live.bilibili.com/gift/v2/gift/bag_list', headers=headers).json()


def give_gift(client, bag_id, gift_num):
    headers = {'cookie': client['cookie']}
    payload = {
        'uid': client['uid'],
        'gift_id': 30607,
        'ruid': client['target_id'],
        'gift_num': gift_num,
        'bag_id': bag_id,
        'platform': 'pc',
        'biz_code': 'Live',
        'biz_id': client['room_id'],
        'storm_beat_id': '0',
        'metadata': '',
        'price': '0',
        'csrf_token': get_csrf(client['cookie']),
        'csrf': get_csrf(client['cookie'])
    }

    js = s.post('https://api.live.bilibili.com/xlive/revenue/v2/gift/sendBag', headers=headers,
                params=payload).json()
    if js['code'] == 0:
        printer(f'uid {client["uid"]} 自动送礼成功')
    else:
        printer(payload)
        printer(f'uid {client["uid"]} 自动送礼失败')


def client_complete(client):
    cursor.execute(f'UPDATE clients_info SET completed = 1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 已完成')


def client_cookie_error(client):
    cursor.execute(f'UPDATE clients_info set cookie_status=-1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 提供的cookie错误 或 已过期')


def client_medal_without(client):
    cursor.execute(f'UPDATE clients_info set medal_status=-1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 没有粉丝牌')


def client_medal_error(client):
    cursor.execute(f'UPDATE clients_info set medal_status=-2 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 所有粉丝牌对应的up都未开通直播间')


def do_bag(client):
    little_heart_num = 0
    bag_id = None

    bag_data = get_bag_data(client)
    if bag_data['code'] != 0:
        printer(bag_data)
        printer(f'uid {client["uid"]} 获取背包数据失败')
        raise ApiException()

    for gift in bag_data['data']['list']:
        if gift['gift_id'] == 30607 and gift['corner_mark'] == '7天':
            little_heart_num = gift['gift_num']
            bag_id = gift['bag_id']

    return little_heart_num, bag_id


async def do_message(uid):
    cursor.execute(f'SELECT * FROM messages_info WHERE msg_status=0 AND uid={uid}')
    rows = cursor.fetchall()
    for row in rows:
        target_id = row[2]
        target_name = row[3]
        room_id = row[4]
        msg = row[5]
        if room_id == '0':
            cursor.execute(f'UPDATE messages_info SET msg_status = -4 WHERE uid ={uid} AND room_id={room_id}')
            printer(f'{target_id}({target_name}) 未开通直播间')
            return

        cursor.execute(f'SELECT cookie FROM clients_info WHERE uid={uid} and cookie_status = -1')
        if cursor.fetchone() is not None:
            cursor.execute(f'UPDATE messages_info SET msg_status = -3 WHERE uid ={uid}')
            return

        cursor.execute(f'SELECT cookie FROM clients_info WHERE uid={uid} and cookie_status = 1')
        row = cursor.fetchone()
        if row is None:
            return

        cookie = row[0]
        headers = {'cookie': cookie}
        try:
            payload = {
                'bubble': 0,
                'msg': msg,
                'color': 16777215,
                'mode': 1,
                'fontsize': 25,
                'rnd': int(time.time()),
                'roomid': room_id,
                'csrf': get_csrf(cookie),
                'csrf_token': get_csrf(cookie)
            }

            res = s.post('https://api.live.bilibili.com/msg/send', headers=headers, params=payload).json()

            if res['msg'] == 'k':
                printer(res)
                printer(f'uid {uid} 给 {target_id}({target_name}) 发送的弹幕 "{msg}" 含有屏蔽词')
                cursor.execute(f'UPDATE messages_info SET msg_status=-1 WHERE uid={uid} AND room_id={room_id}')
                return

            if res['code'] == -403:
                printer(res)
                printer(f'uid {uid} UL等级太低，无法给 {target_id}({target_name}) 发送弹幕 "{msg}" ')
                cursor.execute(f'UPDATE messages_info SET msg_status=-2 WHERE uid={uid} AND room_id={room_id}')
                return
            elif res['code'] == -111 or res['code'] == -101:
                printer(res)
                printer(f'uid {uid} 提供的cookie错误 或 已过期')
                cursor.execute(f'UPDATE clients_info set cookie_status=-1 WHERE uid = {uid}')
            elif res['code'] != 0:
                printer(res)
                printer(f'uid {uid} 给 {target_id}({target_name}) 发送弹幕 "{msg}" 失败')
                raise ApiException()

            cursor.execute(f'UPDATE messages_info SET msg_status=1 WHERE uid={uid} AND room_id={room_id}')
            printer(f'uid {uid} 给 {target_id}({target_name}) 发送弹幕 "{msg}" 成功')
            await asyncio.sleep(3)

        except ApiException:
            raise

        except Exception as er:
            cursor.execute(f'UPDATE clients_info set cookie_status=-1 WHERE uid = {uid}')
            printer(f'uid {uid} 提供的cookie有误，无法被解析')


async def do_x(client, medal, payload):
    await asyncio.sleep(payload['heartbeat_interval'])
    index = 0
    while True:
        response = post_x(client['cookie'], payload, medal['room_id'])
        if response['code'] != 0:
            printer(response)
            printer(f'uid {client["uid"]} 发送X心跳包失败')
            raise ApiException()

        # response['code'] == 1012002   timestamp error
        # response['code'] == 1012003   分区数据错误

        payload['ets'] = response['data']['timestamp']
        payload['secret_key'] = response['data']['secret_key']
        payload['heartbeat_interval'] = response['data']['heartbeat_interval']
        payload['id'][2] += 1

        index += int(payload['heartbeat_interval']) / 60

        if index > 6:
            return

        await asyncio.sleep(payload['heartbeat_interval'])


async def do_client(client):
    i = 0
    tasks = []
    for medal in client['medals']:
        payload = post_e(client['cookie'], medal['room_id'], client['uid'])

        if payload['id'][0] != 0 and payload['id'][1] != 0:
            tasks.append(do_x(client, medal, payload))
            i += 1

        if i == 6:
            break

    before_little_heart_num = do_bag(client)[0]
    await asyncio.gather(*tasks)
    [after_little_heart_num, bag_id] = do_bag(client)

    if after_little_heart_num == 24 or after_little_heart_num == before_little_heart_num:
        client_complete(client)
        if bag_id is not None and client['auto_gift'] == 1:
            give_gift(client, bag_id, after_little_heart_num)
    else:
        printer(f'uid {client["uid"]} 已获取 {after_little_heart_num} 个小心心')


async def main():
    tasks = [do_message(uid) for uid in msg_uid]
    await asyncio.gather(*tasks)

    tasks = [do_client(client) for client in clients]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    while True:
        # noinspection PyBroadException
        try:
            get_msg_uid()
            get_clients()
            get_medals()
            asyncio.run(main())
            cursor.execute('UPDATE bot_info SET app_status=0')
        except ApiException:
            cursor.execute('UPDATE bot_info SET app_status=-1')
            for sleep_minute in range(0, 15):
                printer(f'调用bilibili的API过于频繁，还需冷却 {15 - sleep_minute} 分钟')
                time.sleep(60)

        except requests.exceptions.ConnectionError as err:
            printer(err)

        except Exception:
            exc = traceback.format_exc()
            printer(exc)

        finally:
            clients.clear()
            time.sleep(random.randint(3, 10))
