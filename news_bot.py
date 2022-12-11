import xmltodict, requests, time, pytz, dateutil.parser
from datetime import datetime
from html.parser import HTMLParser
from mastodon import Mastodon

SERVER_URL = "https : //your.server.here"
TOKEN = "YOURTOKENHERE"
MOST_RECENT_X = 5
INTERPOST_DELAY = 60

FEED_URLS = [
    "https://feeds.feedburner.com/securityweek",
    "https://www.darkreading.com/rss.xml",
    "http://rss.cnn.com/rss/cnn_topstories.rss",
    "http://feeds.nytimes.com/nyt/rss/HomePage",
    "http://rssfeeds.usatoday.com/usatoday-newstopstories&x=1",
    "http://www.npr.org/rss/rss.php?id=1001",
    "http://newsrss.bbc.co.uk/rss/newsonline_world_edition/americas/rss.xml",
    "https://www.ed.gov/feed",
    "https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss",
    "http://feeds.wired.com/wired/index",
    "http://feeds.feedburner.com/FrontlineEditorsNotes",
    "http://www.pbs.org/wgbh/nova/rss/nova.xml",
    "http://www.npr.org/rss/rss.php?id=1045",
    "https://www.texasobserver.org/feed/",
    "https://www.chron.com/rss/feed/News-270.php",
    "https://www.chron.com/rss/feed/Politics-275.php",
    "https://www.chron.com/rss/feed/Energy-288.php",
    "https://www.chron.com/rss/feed/Technology-289.php",
    "https://www.chron.com/rss/feed/Economy-292.php",
    "http://feeds.washingtonpost.com/rss/politics",
    "http://feeds.washingtonpost.com/rss/world",
    "https://unicornriot.ninja/feed/",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "https://www.latimes.com/environment/rss2.0.xml",
    "https://www.latimes.com/politics/rss2.0.xml",
    "https://www.ipcc.ch/feed/",
    "https://feeds.nbcnews.com/nbcnews/public/news",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.theguardian.com/us/rss",
    "https://www.theguardian.com/world/rss",
    "https://www.teenvogue.com/feed/rss",
    "https://www.rollingstone.com/feed/",
    "https://theintercept.com/feed/?rss"
]

TZ_STR = '''-12 Y
-11 X NUT SST
-10 W CKT HAST HST TAHT TKT
-9 V AKST GAMT GIT HADT HNY
-8 U AKDT CIST HAY HNP PST PT
-7 T HAP HNR MST PDT
-6 S CST EAST GALT HAR HNC MDT
-5 R CDT COT EASST ECT EST ET HAC HNE PET
-4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
-3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
-2 O BRST FNT PMDT UYST WGST
-1 N AZOT CVT EGT
0 Z EGST GMT UTC WET WT UT
1 A CET DFT WAT WEDT WEST
2 B CAT CEDT CEST EET SAST WAST
3 C EAT EEDT EEST IDT MSK
4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
10 K AEST ChST PGT VLAT YAKST YAPT
11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
13 FJST NZDT
11.5 NFT
10.5 ACDT LHST
9.5 ACST
6.5 CCT MMT
5.75 NPT
5.5 SLT
4.5 AFT IRDT
3.5 IRST
-2.5 HAT NDT
-3.5 HNT NST NT
-4.5 HLV VET
-9.5 MART MIT'''

class HTMLFilter(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

def stripHTML(html):
    f = HTMLFilter()
    f.feed(html)
    return f.text.encode('utf-16','surrogatepass').decode('utf-16')

def consumeItem(item):
    TZD = {}
    for tz_descr in map(str.split, TZ_STR.split('\n')):
        tz_offset = int(float(tz_descr[0]) * 3600)
        for tz_code in tz_descr[1:]:
            TZD[tz_code] = tz_offset
    if 'pubDate' in item and type(item) is not str:
        if item['pubDate'] is not None:
            try:
                item['pubDate'] = dateutil.parser.parse(item['pubDate'], tzinfos=TZD).astimezone(pytz.utc)
            except:
                print("failed to parse pubDate")
                return None

    else:
        print("pubDate doesnt exist, skipping")
        return None
    o = {}
    o['content'] = ""
    if 'title' in item:
        try:
            if item['title'] is not None:
                o['content'] += "%s\n" % (stripHTML(item['title']))
        except:
            return None
    if 'description' in item:
        try:
            if item['description'] is not None:
                o['content'] += "%s\n" % (stripHTML(item['description']))
        except:
            return None
    if 'link' in item:
        try:
            if item['link'] is not None:
                o['content'] += "[%s](%s)\n" % (item['link'],item['link'])
        except:
            return None
    if 'pubDate' in item:
        if item['pubDate'] is not None:
            o['pubDate'] = item['pubDate']
    if 'media:content' in item:
        if item['media:content'] is not None:
            if 'url' in item['media:content']:
                o['media_content_url'] = item['media:content']['url']
    if 'content:encoded' in item:
        o['media_encoded'] = item['content:encoded']
    return o

def main():
    feeds = list()
    posts = dict()
    todays = list()
    i = 0
    for url in FEED_URLS:
        print("fetching [%s]" % (url))
        try:
            r = requests.get(url=url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'})
        except:
            print("failed to fetch xml")
            next
        try:
            xml = xmltodict.parse(r.text)
        except:
            print("failed to parse xml")
            next
        k = MOST_RECENT_X
        for item in xml['rss']['channel']['item']:
            feeds.append(item)
            k -= 1
            if k < 0:
                break
    print("consuming feeds")
    for item in feeds:
        z = consumeItem(item)
        if z is not None:
            posts["%s_%s" % (z['pubDate'], i)] = z
            i += 1
    print("thats %s posts" % (len(feeds)))
    items = sorted(posts.keys())
    for a in items:
        past = datetime.strptime(posts[a]['pubDate'].strftime("%Y/%m/%d"), "%Y/%m/%d")
        present = datetime.now()
        if (past.date() < present.date()):
            pass
        else:
            todays.append(posts[a])
    print("thats %s posts for today" % (len(todays)))
    m = Mastodon(access_token=TOKEN, api_base_url=SERVER_URL)
    j = 1
    for post in todays:
        m.status_post(status=post['content'])
        print("Posted %s/%s. Sleeping for %s seconds." % (j, len(todays), INTERPOST_DELAY))
        time.sleep(INTERPOST_DELAY)
if __name__ == "__main__":
    main()
