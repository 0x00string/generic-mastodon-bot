import xmltodict, requests, time, datetime
from html.parser import HTMLParser
from mastodon import Mastodon

SERVER_URL = "https : //your.server.here"
TOKEN = "YOURTOKENHERE"
FEED_URLS = [
    "http://rss.cnn.com/rss/cnn_topstories.rss",
    "http://feeds.nytimes.com/nyt/rss/HomePage",
    "http://www.washingtonpost.com/rss/",
    "https://www.apnews.com/apf-usnews",
    "http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
    "http://www.npr.org/rss/rss.php?id=1001",
    "http://newsrss.bbc.co.uk/rss/newsonline_world_edition/americas/rss.xml",
    "https://www.ed.gov/feed",
    "http://feeds.nature.com/nature/rss/current",
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
    "http://feeds.washingtonpost.com/rss/politics?itid=lk_inline_manual_2",
    "http://feeds.washingtonpost.com/rss/world?itid=lk_inline_manual_37",
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

class HTMLFilter(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

def stripHTML(html):
    f = HTMLFilter()
    f.feed(html)
    return f.text.encode('utf-16','surrogatepass').decode('utf-16')

def main():
    m = Mastodon(access_token=TOKEN, api_base_url=SERVER_URL)
    feeds = list()
    feeds_dict_by_pubDate = dict()
    for url in FEED_URLS:
        print("fetching [%s]" % (url))
        try:
            r = requests.get(url=url)
        except:
            print("failed to fetch")
            next
        try:
            xml = xmltodict.parse(r.text)
        except:
            print("failed to parse")
            next
        for item in xml['rss']['channel']['item']:
            feeds.append(item)
    print("consuming feeds")
    for item in feeds:
        try:
            feeds_dict_by_pubDate[item['pubDate']] = [''.join(item['title']), stripHTML(''.join(item['description'])), ''.join(item['link'])]# need to try to add media links too, needs ifs and such
        except:
            print("failed to consume [%s]" % (item['title']))
            next
    items = feeds_dict_by_pubDate.keys()
    #sorted_items = sorted(items, key=lambda x: datetime.datetime.strptime(x[:x.rindex(':')-3], '%a, %d %b %Y %H:%M'))#'%a, %d %b %Y %H:%M:%S %z'))
    for a in items:#sorted_items:
        m.status_post(status="-=-=-\nTitle: %s\nDescription: %s\nLink: %s" % (feeds_dict_by_pubDate[a][0], feeds_dict_by_pubDate[a][1], feeds_dict_by_pubDate[a][2]))

if __name__ == "__main__":
    main()
