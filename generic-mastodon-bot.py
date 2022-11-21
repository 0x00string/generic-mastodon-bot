import argparse, urllib.request, sqlite3, datetime, pytz, time, youtube_dl, os.path, json, mastodon
from mastodon import Mastodon

LOGLEVEL = 5
DB_PATH = "./prefs.sqlite3"
DOWNLOAD_METHOD = "direct"
DOWNLOAD_DIRECTORY = "./downloaded/"
DOWNLOAD_REMOTE_URLS = True
POSTS_DIRECOTRY = "./posts/"
MAX_POST_SIZE = 11000

def parseArguments():
    parser = argparse.ArgumentParser(description='python3 script.py -t <mastodon api token> -u https://mastodon.server')
    parser.add_argument('-t','--token', help='mastodon access token', required=True)
    parser.add_argument('-u','--url', help='mastodon server url', required=True)
    return vars(parser.parse_args())

# utility functions

def log(text, category="info"):# all > debug > info > error > none
    if (LOGLEVEL < 1):
        return
    date = str(datetime.datetime.now(pytz.timezone('US/Central')))
    if (("info" in category) and (LOGLEVEL > 1)):
        print("[INFO " + date + "]:" + str(text))
    elif(("debug" in category) and (LOGLEVEL > 2)):
        print("[DEBUG " + date + "]:" + str(text))
    elif(("error" in category) and (LOGLEVEL > 0)):
        print("[ERROR " + date + "]:" + str(text))
    else:
        print("[MISC " + date + "]:" + str(text))

def getFreeSpace():
    statvfs = os.statvfs('/')
    return ((statvfs.f_frsize * statvfs.f_bavail) / 1073741824) # in gigabytes

# auth, etc

def authenticate(url, token):
    return Mastodon(access_token=token, api_base_url=url)

# database stuff

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

# notifications

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
    print("\\\n%s\n/" % (noti['status']['content']))

def processReblog(noti):
    log("%s boosted" % (noti['account']['acct']))
    print("\\\n%s\n/" % (noti['status']['content']))

def processMention(noti):
    log("%s mentioned" % (noti['account']['acct']))
    #if (getPostRepliedTo(noti['status'])):
    #    print("" % s (), )
    print("\\\n%s\n/" % (noti['status']['content']))

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

# posts

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
    return m.status_post(status, in_reply_to_id=in_reply_to_id, media_ids=media_ids, sensitive=sensitive, visibility=visibility, spoiler_text=spoiler_text, language=language, idempotency_key=idempotency_key, content_type=content_type, scheduled_at=scheduled_at, poll=poll)

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

# download functions

def httpDownload(url, local_save_path):
    if DOWNLOAD_METHOD == "direct":
        downloadUrllibDirect(url, local_save_path)
    else:
        log("unrecognized download method", "error")

def downloadUrllibDirect(url, local_save_path):
    filename = urllib.request.urlopen(urllib.request.Request(url, method='HEAD')).info().get_filename()
    urllib.request.urlretrieve(url, local_save_path + filename)

# youtube-dl

class ytdl_logger(object):
    def debug(self, msg):
        log(msg, "debug")

    def warning(self, msg):
        log(msg, "debug")

    def error(self, msg):
        log(msg, "error")

def ytdl_hook(d):
    print(d['status'])
    if d['status'] == 'finished':
        print('download completed')

def list_playlist_urls(playlist_url):
    out = []
    with youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s', 'quiet':True,}) as ydl:
        result = ydl.extract_info(playlist_url, download=False)
        if 'entries' in result:
            video = result['entries']
            for i, item in enumerate(video):
                v = result['entries'][i]['webpage_url']
                out.append(v)
    return out

def download_video(video_url):
    video_ydl_opts = {
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
        'logger': ytdl_logger(),
        'progress_hooks': [ytdl_hook],
    }
    with youtube_dl.YoutubeDL(video_ydl_opts) as ydl:
        ydl.download([video_url])

def download_audio(audio_url):
    audio_ydl_opts = {
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
        'logger': ytdl_logger(),
        'progress_hooks': [ytdl_hook],
    }
    with youtube_dl.YoutubeDL(audio_ydl_opts) as ydl:
        ydl.download([audio_test_url])

# websocket streaming

def processAnnouncementReaction(reaction):
    pass

class StreamListener(mastodon.StreamListener):
    def on_notification(self, notification):
        processNotificationStreaming(notification)

    def on_abort(self, err):
        log(err, 'error')

    def on_conversation(self, conversation):
        processDM(conversation)

    def on_unknown_event(self, name, event):
        log("not sure what this is", "error")
        log(name, "error")
        log(json.dumps(event, indent=4, sort_keys=False, default=str), "error")

    def handle_heartbeat(self):
        pass
        #log('exchanged heartbeats with the server','debug')

    def on_announcement_reaction(self, reaction):
        processAnnouncementReaction(reaction)

    def on_status_update(self, blah):
        pass

def startStreaming(m):
    listener = StreamListener()
    m.stream_user(listener)

def startStreamingAsync(m):
    listener = StreamListener()
    return m.stream_user(listener, run_async=True, reconnect_async=True, reconnect_async_wait_sec=5)

# main loop

def main():
    args = parseArguments()
    dbCheck()
    db = connectDB()
    last_read = getTimelineIndex(db, "notifications")
    m = authenticate(args['url'], args['token'])
    stream_handle = startStreamingAsync(m)
    while stream_handle.is_alive():
        log('checking stream handle is receiving','debug')
        log('%s' % (stream_handle.is_receiving()),'debug')
        log('checking last read notification index','debug')
        n = getNotificationsFromIndex(m, last_read)
        if len(n) > 0:
            last_read = n[0]['id']
            log('updating last read notification: %s' % (last_read),'debug')
            if not last_read:
                setTimelineIndex(db, 'notifications', last_read)
        log('sleeping main 5 minutes','debug')
        time.sleep(300)
    stream_handle.close()

if __name__ == "__main__":
    main()
