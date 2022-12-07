import argparse, urllib.request, sqlite3, datetime, pytz, time, youtube_dl, os.path, json, mastodon, random, re
from mastodon import Mastodon
from html.parser import HTMLParser

DB_PATH = "./prefs.sqlite3"
YTDL_VERBOSE = False
DOWNLOAD_METHOD = "direct"
DOWNLOAD_DIRECTORY = "./downloaded/"
DOWNLOAD_REMOTE_URLS = True
POSTS_DIRECOTRY = "./posts/"
MAX_POST_SIZE = 11000
PJSC_KEY = ""

def parseArguments():
    parser = argparse.ArgumentParser(description='python3 script.py -t <mastodon api token> -u https://mastodon.server')
    parser.add_argument('-t','--token', help='mastodon access token', required=True)
    parser.add_argument('-u','--url', help='mastodon server url', required=True)
    return vars(parser.parse_args())

def log(message, category='info'):
    print('[%s][%s]: %s' % (category, str(datetime.datetime.now(pytz.timezone('US/Central')).strftime("%Y-%m-%d %H:%M:%S")), message))

def getFreeSpace():
    statvfs = os.statvfs('/')
    return ((statvfs.f_frsize * statvfs.f_bavail) / 1073741824) # in gigabytes

class HTMLFilter(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

def stripHTML(html):
    f = HTMLFilter()
    f.feed(html)
    return f.text.encode('utf-16','surrogatepass').decode('utf-16')

def hideHashtags(text):# [](#hidehashtags), content_type=text/markdown
    return re.sub(r'(#[a-zA-Z0-9_]+)', r'\[\]\(\\1\)', text)

def spongeCase(text):# LiKe tHiS
    d = 0
    o = ""
    for c in text:
        if d == 0:
            d = 1
            o += c.upper()
        else:
            d = 0
            o += c.lower()
    return o

def erraticFormatting(text):# randomly switch between markdown formattings
    o = ""
    m = {
        '0': ['\n# ','\n'], # headings
        '1': ['\n## ','\n'],
        '2': ['\n### ','\n'],
        '3': ['\n#### ','\n'],
        '4': ['\n##### ','\n'],
        '5': ['\n###### ','\n'],
        '6': ['**','** '], # bold
        '7': ['*','* '], # italic
        '8': ['***','*** '], # bold italic
        '9': ['\n> ','\n'], # block quote
        '10': ['\n>> ','\n'], # nested block quote
        '11': ['\n>> # ','\n'],
        '12': ['\n>> - ','\n'],
        '13': ['\n>> 1. ','\n'],
        '14': ['\n- ','\n'],
        '15': ['`','` '],
        '16': ['```\n','\n```'],
        '17': ['\n>> `','`\n'],
        '18': ['\n69. ','\n'],
        '19': ['\n420. ','\n'],
    }
    for a in text.split():
        r = m[str(random.randrange(len(m)))]
        o += "%s%s%s" % (r[0], a, r[1])
    return o

def authenticate(url, token):
    return Mastodon(access_token=token, api_base_url=url)

def createDB(path = os.path.join(os.path.dirname(__file__), DB_PATH)):
    db = connectDB()
    cur = db.cursor()
    sql1 = """
    CREATE TABLE timelines (
        id integer PRIMARY KEY,
        timeline text NOT NULL,
        mindex text NOT NULL)"""
    try:
        cur.execute(sql1)
        db.commit()
    finally:
        cur.close()
    addTimeline(db, "notifications")
    db.close()

def connectDB(path = os.path.join(os.path.dirname(__file__), DB_PATH)):
    db = sqlite3.connect(path)
    return db

def setTimelineIndex(db, timeline_name, index):
    cur = db.cursor()
    sql = "UPDATE timelines SET mindex=? WHERE timeline=?"
    try:
        cur.execute(sql, (index, timeline_name))
        db.commit()
    finally:
        cur.close()

def getTimelineIndex(db, timeline_name):
    index = None
    cur = db.cursor()
    sql = "SELECT mindex FROM timelines WHERE timeline=?"
    try:
        cur.execute(sql, (timeline_name,))
        index = cur.fetchall()
    finally:
            cur.close()
    return index[0][0]

def listTimelines(db):
    timelines = None
    cur = db.cursor()
    sql = "SELECT timeline FROM timelines"
    try:
        cur.execute(sql)
        timelines = cur.fetchall()
    finally:
            cur.close()
    return timelines

def addTimeline(db, timeline_name):
    cur = db.cursor()
    sql = "INSERT INTO timelines (timeline, mindex) VALUES ( ?, ? )"
    try:
        cur.execute(sql, (timeline_name, "0"))
        db.commit()
    finally:
        cur.close()

def delTimeline(db, timeline_name):
    cur = db.cursor()
    sql = "DELETE * FROM timelines WHERE timeline=?"
    try:
        cur.execute(sql, (timeline_name,))
        db.commit()
    finally:
        cur.close()

def dbCheck():
    if not os.path.isfile(DB_PATH):
        createDB()
        log('DB created','info')

def getCurrentNotificationsIndex(db):
    return getTimelineIndex(db, "notifications")

def setCurrentNotificationsIndex(db, index):
    setTimelineIndex(db, "notifications", index)

def getNotificationsFromIndex(m, index):
    return m.notifications(since_id=index)

def getNotification(m, not_id):
    return m.notifications(id=not_id)

def processDM(noti):
    log("%s DMed" % (noti['account']['acct']))

def processFavourite(noti):
    log("%s favorited" % (noti['account']['acct']))
    print("\\\n%s\n/" % (stripHTML(noti['status']['content'])))

def processReblog(noti):
    log("%s boosted" % (noti['account']['acct']))
    print("\\\n%s\n/" % (stripHTML(noti['status']['content'])))

def processMention(noti):
    log("%s mentioned" % (noti['account']['acct']))
    #if (getPostRepliedTo(noti['status'])):
    #    print("" % s (), )
    print("\\\n%s\n/" % (stripHTML(noti['status']['content'])))

def processFollow(noti):
    log("%s followed" % (noti['account']['acct']))

def processNotifications(m, last_read_notification=None):
    n = getNotificationsFromIndex(m, last_read_notification)
    if (not n):
        log('No new notificaitons', 'info')
        return last_read_notification
    last_read_notification = n[0]['id']
    n.reverse()
    for i in n:
        if i['type'] == 'follow':
            processFollow(i)
        elif i['type'] == 'favourite':
            processFavourite(i)
        elif i['type'] == 'reblog':
            processReblog(i)
        elif i['type'] == 'mention':
            processMention(i)
        else:
            log("not sure what this is", "error")
            log(i['type'], "error")
            log(json.dumps(i, indent=4, sort_keys=False, default=str), "error")
    return last_read_notification

def processNotificationStreaming(notification):
    if notification['type'] == 'follow':
        processFollow(notification)
    elif notification['type'] == 'favourite':
        processFavourite(notification)
    elif notification['type'] == 'reblog':
        processReblog(notification)
    elif notification['type'] == 'mention':
        processMention(notification)
    else:
        log("not sure what this is", "error")
        log(notification['type'], "error")
        log(json.dumps(notification, indent=4, sort_keys=False, default=str), "error")

def uploadImages(m, image_path_array):
    media_list = list()
    for i in image_path_array:
        try:
            t = m.media_post(i)
        except:
            log("failed to upload [%s]" % (i), "error")
            return
        media_list.append(t['id'])
    return media_list

def sendPost(m, status, in_reply_to_id=None, media_ids=None, sensitive=False, visibility=None, spoiler_text=None, language=None, idempotency_key=None, content_type=None, scheduled_at=None, poll=None):
    return m.status_post(   status,
                            in_reply_to_id=in_reply_to_id, 
                            media_ids=media_ids, # list of up to 4 media IDs or media dicts as returned by media_post()
                            sensitive=sensitive, # True/False
                            visibility=visibility, # 'direct' - mentioned, 'private' - followers, 'unlisted', 'public'
                            spoiler_text=spoiler_text, 
                            language=language, # ISO 639-2 language codes
                            idempotency_key=idempotency_key, # unique key to prevent double post
                            content_type=content_type, # 'text/markdown', 'text/html', 'text/plain'
                            scheduled_at=scheduled_at, 
                            poll=poll)# poll object as returned by make_poll()

def getPost(m, post_id):
    return m.status(id)

def getPostMedia(post):
    a = m.status(id)
    if len(a['media_attachments']) > 0:
        return a['media_attachments']
    else:
        return None

def downloadPostMedia(post):
    path_prefix = DOWNLOAD_DIRECTORY + post['account']['acct'] + "-" + post['id']
    with open(path_prefix + ".json", 'a') as out:
        out.write(json.dumps(i, sort_keys=False, default=str))
    for media_attachment in post['media_attachments']:
        if ((len(media_attachment['url']) > 0)):
            httpDownload(media_attachment['url'], path_prefix + "-" + media_attachment['id'] + "-")
        elif ((len(media_attachment['remote_url']) > 0 and DOWNLOAD_REMOTE_URLS)):
            httpDownload(media_attachment['remote_url'], path_prefix + "-" + media_attachment['id'] + "-")
        else:
            log("no local url available, remote URL download not permitted, bailing on [%s]" % (media_attachment['remote_url']), "error")

def unrollThread(m, post):
    thread = list()
    while True:
        thread.append(post)
        if (len(post['in_reply_to_id']) < 1):
            break
        post = m.status(post['in_reply_to_id'])
    thread.reverse()
    return thread

def getPostRepliedTo(post):
    if (len(post['in_reply_to_id']) > 0):
        return post['in_reply_to_id']
    else:
        return None

def getThreadOP(m=None, post=None, thread=None):
    if thread is None:
        if ((m is None) or (post is None)):
            log("if not providing a thread, must provide mastodon object and post id", "error")
        thread = unrollThread(m, post)
    return thread[0]['account']['acct']

def httpDownload(url, local_save_path):
    if DOWNLOAD_METHOD == "direct":
        downloadUrllibDirect(url, local_save_path)
    else:
        log("unrecognized download method", "error")

def downloadUrllibDirect(url, local_save_path):
    filename = urllib.request.urlopen(urllib.request.Request(url, method='HEAD')).info().get_filename()
    urllib.request.urlretrieve(url, local_save_path + filename)

class ytdlLogger(object):
    def debug(self, msg):
        if (YTDL_VERBOSE):
            log(msg, "YTDL")

    def warning(self, msg):
        if (YTDL_VERBOSE):
            log(msg, "YTDL")

    def error(self, msg):
        if(YTDL_VERBOSE):
            log(msg, "YTDL")

def ytdlHook(d):
    if d['status'] == 'finished':
        if(YTDL_VERBOSE):
            log('Status: %s' % (d['status']),'YTDL')
            log('filename: %s' % (d['filename']),'YTDL')
            log('downloaded_bytes: %s' % (d['downloaded_bytes']),'YTDL')
            log('elapsed: %s' % (d['elapsed']),'YTDL')
    if d['status'] == 'downloading':
        if(YTDL_VERBOSE):
            log('Status: %s' % (d['status']),'YTDL')
            log('filename: %s' % (d['filename']),'YTDL')
            log('tmpfilename: %s' % (d['tmpfilename']),'YTDL')
            log('downloaded_bytes: %s' % (d['downloaded_bytes']),'YTDL')
            log('total_bytes: %s' % (d['total_bytes']),'YTDL')
            log('total_bytes_estimate: %s' % (d['total_bytes_estimate']),'YTDL')
            log('elapsed: %s' % (d['elapsed']),'YTDL')
            log('eta: %s' % (d['eta']),'YTDL')
            log('speed: %s' % (d['speed']),'YTDL')
            log('fragment_index: %s' % (d['fragment_index']),'YTDL')
            log('fragment_count: %s' % (d['fragment_count']),'YTDL')
    if d['status'] == 'error':
        log('oops, error in ytdl download:\n%s' % (d),'error')
        # here we would re-queue


video_opts = {
    'outtmpl': DOWNLOAD_DIRECTORY + '%(title)s.%(ext)s',
    'format': 'bestvideo+bestaudio',
    'no_color': True,
    'nooverwrites': True,
    'restrictfilenames': True,
    'call_home': False,
    'writedescription': True,
    'writeinfojson': True,
    'ignoreerrors': True,
    'continuedl': True,
    'download_archive': "video_archive.txt",
    'logger': ytdlLogger(),
    'progress_hooks': [ytdlHook],
}

audio_opts = {
    'outtmpl': DOWNLOAD_DIRECTORY + '%(title)s.%(ext)s',
    'format': 'bestaudio/best',
    'no_color': True,
    'nooverwrites': True,
    'restrictfilenames': True,
    'call_home': False,
    'writedescription': True,
    'writeinfojson': True,
    'ignoreerrors': True,
    'continuedl': True,
    'download_archive': "audio_archive.txt",
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'logger': ytdlLogger(),
    'progress_hooks': [ytdlHook],
}

def ytdlGetPlaylistUrls(playlist_url):
    out = []
    with youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s', 'quiet':True,}) as ydl:
        result = ydl.extract_info(playlist_url, download=False)
        if 'entries' in result:
            video = result['entries']
            for i, item in enumerate(video):
                v = result['entries'][i]['webpage_url']
                out.append(v)
    return out

def ytdlDownload(url, opts=video_opts):
    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download([url])

def phantomJSCloudRender(url_to_render, output_file_path, render_format="png", height=800, width=600, key=PJSC_KEY):
    b = "https://phantomjscloud.com/api/browser/v2/%s/" % (key)
    h = {'content-type':'application/json'}
    p = {"pages":[{"url": url_to_render,"renderType": render_format,"outputAsJson": True,"renderSettings": {"viewport": {"height": height,"width": width}}}]}
    req = urllib.request.Request(b, json.dumps(p).encode('utf-8'), h)
    res = urllib.request.urlopen(req)
    rj = json.loads(res.read())
    if (str(res.headers['pjsc-content-status-code']) in "200"):
        with open( "%s.%s" % (output_file_path, render_format), "wb") as rf:
            rf.write(base64.b64decode(rj['content']['data']))

class StreamListener(mastodon.StreamListener):
    def on_notification(self, notification):
        processNotificationStreaming(notification)

    def on_abort(self, err):
        log(err, 'error')

    def on_conversation(self, conversation):
        processDM(conversation)

    def handle_heartbeat(self):
        pass

    def on_announcement_reaction(self, reaction):
        pass

    def on_status_update(self, blah):
        pass

    def on_update(self, update):
        pass

    def on_unknown_event(self, name, event):
        log("not sure what this is", "error")
        log(name, "error")
        log(json.dumps(event, indent=4, sort_keys=False, default=str), "error")

def startStreaming(m):
    listener = StreamListener()
    m.stream_user(listener)

def startStreamingAsync(m):
    listener = StreamListener()
    return m.stream_user(listener, run_async=True, reconnect_async=True, reconnect_async_wait_sec=5)

def main():
    args = parseArguments()
    dbCheck()
    db = connectDB()
    last_read = getTimelineIndex(db, "notifications")
    m = authenticate(args['url'], args['token'])
    stream_handle = startStreamingAsync(m)
    while stream_handle.is_alive():
        #log('checking stream handle is receiving','debug')
        #log('%s' % (stream_handle.is_receiving()),'debug')
        n = getNotificationsFromIndex(m, last_read)
        if len(n) > 0:
            last_read = n[0]['id']
            log('updating last read notification: %s' % (last_read),'debug')
            setTimelineIndex(db, 'notifications', last_read)
        time.sleep(300)
    stream_handle.close()

if __name__ == "__main__":
    main()
