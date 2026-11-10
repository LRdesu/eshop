import json, urllib.request

BASE = 'http://127.0.0.1:8000'
PW = bytes([49, 50, 51, 52, 53, 54]).decode()


def req(path, method='GET', payload=None, token=None):
    r = urllib.request.Request(BASE + path, data=json.dumps(payload).encode() if payload is not None else None, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())


def login(u):
    return req('/api/v1/auth/login', 'POST', {'username': u, 'password': PW})['data']['token']

tok = login('bob')  # 用 bob 测试（今天还没签到）
me0 = req('/api/v1/members/me', token=tok)['data']
print('[0] bob 签到前金币:', me0.get('points'))

d = req('/api/v1/members/checkin', 'POST', token=tok)
print('[1] 首次签到:', 'code=' + str(d['code']), '奖励', d['data']['reward'], '余额', d['data']['points'])

d2 = req('/api/v1/members/checkin', 'POST', token=tok)
print('[2] 重复签到:', 'code=' + str(d2['code']), 'msg=', d2.get('msg'))
