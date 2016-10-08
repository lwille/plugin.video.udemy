import json
import os
import requests

from xbmcswift2 import Plugin

plugin = Plugin()

headers = {'user-agent': plugin.name + '/' + plugin.addon.getAddonInfo('version')}
base_url = 'https://www.udemy.com/api-2.0'

csrfmiddlewaretoken = 'kTpO8iKchEetelPpjDHDZ4XhMEAzwUd1'

my_courses_url = "%s/users/me/subscribed-courses" % base_url
courses_url = "%s/courses" % base_url
login_url = "https://www.udemy.com/join/login-popup/?display_type=popup&locale=en_US&response_type=json&next=https%3A%2F%2Fwww.udemy.com"

cookie_jar = requests.cookies.RequestsCookieJar()
cookie_jar.set('csrftoken', csrfmiddlewaretoken)


def login():
    plugin.notify("Logging you in as %s" % setting_get('user_email'), None, 1000)
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

    r = requests.post(login_url, data={
        'csrfmiddlewaretoken': csrfmiddlewaretoken,
        'email': setting_get('user_email'),
        'password': setting_get('user_password'),
        'locale': 'en_US'
    }, headers=login_headers, cookies=cookie_jar)
    print(json.dumps(r.cookies.get_dict()))
    print(r.content)
    r.raise_for_status()
    headers['X-Udemy-Authorization'] = headers['Authorization'] = "Bearer %s" % r.cookies['access_token']


def setting_get(key):
    if os.environ.get('SETTINGS'):
        return json.loads(os.environ['SETTINGS']).get(key)
    return plugin.get_setting(key)


#
def get_menu_items():
    return [
        (plugin.url_for('courses'), 30001),
    ]


def load_json(url, params=None):
    r = requests.get(url, params=params, headers=headers, cookies=cookie_jar)
    r.raise_for_status()
    return r.json()


def ensure_login():
    if not cookie_jar.get('access_token'):
        login()


@plugin.route('/')
def index():
    return [{
        'label': 'Courses',
        'path': plugin.url_for('courses')
    }]


@plugin.route('/course/<cid>/play/<title>', name='course_play')
def play(cid, title):
    return None


@plugin.route('/course/<cid>', name='course_details')
def show_course_details(cid):
    ensure_login()
    course = load_json("%s/%s/public-curriculum-items" % (courses_url, cid))
    print json.dumps(course)

    items = []
    lectures = filter(lambda result: result['_class'] == 'lecture', course['results'])

    for lecture in lectures:
        items.append({
            'label': lecture['title'],
            'path': plugin.url_for('course_play', cid=cid, title=lecture['asset']['title'])
        })

    return plugin.finish(items)


@plugin.route('/courses', name='courses')
def show_courses():
    ensure_login()
    plugin.notify("Loading courses for %s" % setting_get('user_email'), None, 1000)
    courses = load_json(my_courses_url)

    items = []
    for course in courses['results']:
        item = {
            'label': course['title'],
            'path': plugin.url_for('course_details', cid=course['id']),
            'thumbnail': course['image_480x270'],
            'info_type': 'video',
            'properties': {
                'fanart_image': course['image_480x270'],
            },
        }
        items.append(item)
    return plugin.finish(items)

    # items = []
    # for video in data[listing_key]:
    #     item = create_item(video.get('VDO'), {'show_airtime': plugin.request.args.get('date'),
    #                                           'show_deletetime': sort == 'LAST_CHANCE',
    #                                           'show_views': sort == 'VIEWS'})
    #     # item['info']['mpaa'] = video.get('mediaRating' + language[0])
    #     items.append(item)
    # return plugin.finish(items)


if __name__ == '__main__':
    plugin.run()
