import json
import os
import requests
import re

from xbmcswift2 import Plugin

plugin = Plugin()

headers = {'user-agent': plugin.name + '/' + plugin.addon.getAddonInfo('version'),
           'Origin': 'https://www.udemy.com',
           'X-Requested-With': 'XMLHttpRequest',
           'Referer': 'https://www.udemy.com/',
           'Accept-Language': 'en-US,en', }
base_url = 'https://www.udemy.com'

my_courses_url = "%s/api-2.0/users/me/subscribed-courses" % base_url
courses_url = "%s/api-2.0/courses" % base_url
login_url = "%s/join/login-popup/" % base_url

cookie_jar = requests.cookies.RequestsCookieJar()

addon_id = plugin._addon.getAddonInfo('id')
icon = 'special://home/addons/%s/icon.png' % addon_id


def login():
    debug_notify("Logging you in as %s" % setting_get('user_email'))
    login_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.udemy.com',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': headers['user-agent'],
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.udemy.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en',
    }
    login_params = 'display_type=popup&locale=en_US&response_type=json&next=https%3A%2F%2Fwww.udemy.com%2F'

    # We need this preflight to get hold of a csrf token.
    r = requests.get(login_url, params=login_params, cookies=cookie_jar, headers=headers)
    r.raise_for_status()
    # seems that csrf cookie isn't tracked properly, so we make sure to store it
    cookie_jar['csrftoken'] = r.cookies.get('csrftoken')
    r = requests.post(login_url, data={
        'csrfmiddlewaretoken': r.cookies.get('csrftoken'),
        'email': setting_get('user_email'),
        'password': setting_get('user_password'),
        'locale': 'en_US'
    }, headers=login_headers, cookies=cookie_jar, params=login_params)

    r.raise_for_status()
    headers['X-Udemy-Authorization'] = headers['Authorization'] = "Bearer %s" % r.cookies.get('access_token')


def debug_notify(msg):
    if setting_get('debug'):
        plugin.notify(msg, None, 1000, icon)
    print(msg)

def setting_get(key):
    if os.environ.get('SETTINGS'):
        return json.loads(os.environ['SETTINGS']).get(key)
    return plugin.get_setting(key)

def get_menu_items():
    return [
        (plugin.url_for('courses'), 30001),
    ]


def load_json(url, params=None):
    r = requests.get(url, params=params, headers=headers, cookies=cookie_jar)
    r.raise_for_status()
    return r.json()


def ensure_login():
    if not headers.has_key('X-Udemy-Authorization'):
        login()


@plugin.route('/')
def index():
    return [{
        'label': 'Courses',
        'path': plugin.url_for('courses')
    }]


@plugin.route('/course/<course_id>/play/<lecture_id>', name='course_play')
def play(course_id, lecture_id):
    ensure_login()
    url = my_courses_url + '/%s/lectures/%s' % (course_id, lecture_id)
    video = load_json(url, params='fields%5Basset%5D=@min,stream_urls,file,label')
    asset = video.get('asset', {})
    files = asset.get('stream_urls', {}).get('Video', [])
    first_file = files[0]

    print first_file
    plugin.set_resolved_url(first_file['file'])


@plugin.route('/course/<course_id>/details/<page>', name='course_details')
def show_course_details(course_id, page):
    ensure_login()
    url = my_courses_url + '/%s/lectures?page=%s' % (course_id, page)
    course = load_json(url)

    items = []
    lectures = filter(lambda result: result['_class'] == 'lecture', course['results'])

    for lecture in lectures:
        items.append({
            'label': lecture['title'],
            'path': plugin.url_for('course_play', course_id=course_id, lecture_id=lecture['id']),
            'info': {
                'label': lecture['title'],
                'title': lecture['title'],
                'plot': lecture['description'],
                'year': lecture['created']
            },
            'is_playable': True,
            'info_type': 'video',
        })

    if course['next']:
        next = course['next']
        pageNo = re.search(r'\d+', next[::-1]).group()[::-1]
        items.append({
            'label': 'next',
            'path': plugin.url_for('course_details', course_id=course_id, page=pageNo),
        })

    return plugin.finish(items)


def _load_courses():
    debug_notify("Loading courses for %s" % setting_get('user_email'))
    next = my_courses_url
    while next:
        response = load_json(next)
        for item in response['results']:
            yield item
        next = response.get('next') \


@plugin.route('/courses', name='courses')
def show_courses():
    ensure_login()

    items = list(map(lambda course: {
        'label': course['title'],
        'path': plugin.url_for('course_details', course_id=course['id'], page='1'),
        'thumbnail': course['image_480x270'],
        'info_type': 'video',
        'properties': {
            'fanart_image': course['image_480x270'],
        },
    }, _load_courses()))

    return plugin.finish(items)


if __name__ == '__main__':
    plugin.run()
