import requests, time, re, pymysql, asyncio, traceback

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


# mysql->python
def get_clients():
    global clients
    cursor.execute('SELECT * FROM clients_info')
    results = cursor.fetchall()
    for row in results:
        # completed or cookie expire or medal invalid
        if row[3] == 1 or row[6] == 1 or row[7] == 1:
            continue

        clients.append({
            'uid': row[0],
            'cookie': row[1],
            'auto_gift': row[2],
            'room_id': row[4],
            'target_id': row[5],
            'little_heart_num': row[8]
        })

    clients = clients[:10]
    # printer(f'get_clients: clients size = {len(clients)}')


# room_id medal_id...
def get_medal():
    global clients
    for client in clients[:]:
        try:
            headers = {'cookie': client['cookie']}
            js = s.get('https://api.bilibili.com/x/web-interface/nav', headers=headers).json()
            if js['code'] != 0:
                client_cookie_expire(client)
                continue
        except Exception:
            client_cookie_expire(client)
            continue

        js = s.get('https://api.live.bilibili.com/i/ajaxGetMyMedalList', headers=headers).json()
        if js['code'] != 0:
            printer(f'{client["uid"]} 获取粉丝牌列表失败')
            raise ApiException()

        if not js['data']:
            client_medal_invalid(client)
            continue

        client['medal'] = []
        medals = []
        for data in js['data']:
            medals.append({
                'target_id': data['target_id'],
                'target_name': data['target_name'],
                'medal_id': data['medal_id'],
                'today_intimacy': data['today_intimacy'],
                'room_id': 0
            })

        i = 0
        for medal in medals:
            js = s.get(
                f"http://api.live.bilibili.com/live_user/v1/Master/info?uid={medal['target_id']}").json()

            if js['code'] != 0:
                printer(f'uid {client["uid"]} 获取room_id失败')
                raise ApiException()

            if js['data']['room_id'] == 0:
                continue

            medal['room_id'] = js['data']['room_id']
            client['medal'].append(medal)

            i += 1
            if i == 12:
                break

        if not client['medal']:
            client_medal_invalid(client)

    clients = clients[:5]
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
    print(payload)

    js = s.post('https://api.live.bilibili.com/xlive/revenue/v2/gift/sendBag', headers=headers,
                params=payload).json()
    if js['code'] == 0:
        printer(f'uid {client["uid"]} 自动送礼成功')
    else:
        printer(f'uid {client["uid"]} 自动送礼失败')


def client_complete(client):
    cursor.execute(f'UPDATE clients_info SET completed = 1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 已完成')


def client_cookie_expire(client):
    cursor.execute(f'UPDATE clients_info set cookie_expire = 1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 提供的cookie无效 或 已失效过期')


def client_medal_invalid(client):
    cursor.execute(f'UPDATE clients_info set medal_invalid = 1 WHERE uid = {client["uid"]}')
    clients.remove(client)
    printer(f'uid {client["uid"]} 没有粉丝牌 或 粉丝牌对应的up都未开通直播间')


def do_bag(client):
    little_heart_num = 0
    bag_id = None

    bag_data = get_bag_data(client)
    if bag_data['code'] != 0:
        printer(f'uid {client["uid"]} 获取背包数据失败')
        raise ApiException()

    for gift in bag_data['data']['list']:
        if gift['gift_id'] == 30607 and gift['corner_mark'] == '7天':
            little_heart_num = gift['gift_num']
            bag_id = gift['bag_id']

    return little_heart_num, bag_id


async def do_x(client, medal, payload):
    await asyncio.sleep(payload['heartbeat_interval'])
    index = 0
    while True:
        response = post_x(client['cookie'], payload, medal['room_id'])
        if response['code'] != 0:
            printer(response)
            printer(f'uid {client["uid"]} 发送X心跳包失败')
            if response['code'] == 1012003:
                printer(f'payload: {payload}')
                return
                # {'id': [0, 0, 1, 11027533], 'device': '["AUTO8716422349901853","3E739D10D-174A-10DD5-61028-A5E3625BE56450692infoc"]', 'ts': 1645035410000, 'is_patch': 0, 'heart_beat': [], 'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36', 'csrf_token': '9d106ffca17096000833d2b9d2abd434', 'csrf': '9d106ffca17096000833d2b9d2abd434', 'visit_id': '', 'ets': 1645035410, 'secret_key': 'seacasdgyijfhofiuxoannn', 'heartbeat_interval': 60, 'secret_rule': [2, 5, 1, 4]}
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
    tasks = []
    i = 0
    for medal in client['medal']:
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
        cursor.execute(
            f'UPDATE clients_info SET little_heart_num={after_little_heart_num} WHERE uid={client["uid"]}')
        printer(f'uid {client["uid"]} 已获取 {after_little_heart_num} 个小心心')


async def main():
    tasks = []
    for client in clients:
        tasks.append(do_client(client))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    while True:
        # noinspection PyBroadException
        try:
            get_clients()
            get_medal()
            asyncio.run(main())

        except ApiException:
            for sleep_minute in range(0, 15):
                printer(f'调用bilibili的API过于频繁，还需冷却 {15 - sleep_minute} 分钟')
                time.sleep(60)

        except Exception:
            exc = traceback.format_exc()
            printer(exc)

        finally:
            clients.clear()
            time.sleep(5)
