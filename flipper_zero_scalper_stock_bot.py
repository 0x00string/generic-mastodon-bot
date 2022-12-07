import requests, time
from html.parser import HTMLParser
from mastodon import Mastodon

SERVER_URL = "https : //your.server.here"
TOKEN = "YOURTOKENHERE"
DELAY = 3600

class LinksParser_flipperzero(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.recording = 0
    self.data = []

  def handle_starttag(self, tag, attributes):
    if tag != 'span':
      return
    if self.recording:
      self.recording += 1
      return
    for name, value in attributes:
      if name == 'data-add-to-cart-text' and value == None:
        break
    else:
      return
    self.recording = 1

  def handle_endtag(self, tag):
    if tag == 'span' and self.recording:
      self.recording -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

class LinksParser_lab401(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.recording = 0
    self.data = []

  def handle_starttag(self, tag, attributes):
    if tag != 'link':
      return
    if self.recording:
      self.recording += 1
      return
    for name, value in attributes:
      if name == 'itemprop' and value == 'availability':
        break
    else:
      return
    self.recording = 1

  def handle_endtag(self, tag):
    if tag == 'link' and self.recording:
      self.recording -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

class LinksParser_hackerwarehouse(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.recording = 0
    self.data = []

  def handle_starttag(self, tag, attributes):
    if tag != 'p':
      return
    if self.recording:
      self.recording += 1
      return
    for name, value in attributes:
      if name == 'class' and value == 'stock in-stock':
        break
    else:
      return
    self.recording = 1

  def handle_endtag(self, tag):
    if tag == 'p' and self.recording:
      self.recording -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

def isFlipperZeroDevBoardSoldOut1():
    r = requests.get("https://shop.flipperzero.one/products/wifi-devboard")
    html = r.text
    p = LinksParser_flipperzero()
    p.feed(html)
    if ("Sold out" in p.data[0]):
        return True
    else:
        return False

def isFlipperZeroSoldOut1():
    r = requests.get("https://shop.flipperzero.one/")
    html = r.text
    p = LinksParser_flipperzero()
    p.feed(html)
    if ("Sold out" in p.data[0]):
        return True
    else:
        return False

def isFlipperZeroDevBoardSoldOut2():
    r = requests.get("https://lab401.com/products/flipper-zero-wifi-devboard?variant=42938105004262")
    html = r.text
    p = LinksParser_lab401()
    p.feed(html)
    if ("Default Title - Sold Out" in "".join(p.data)):
        return True
    else:
        return False

def isFlipperZeroSoldOut2():
    r = requests.get("https://lab401.com/products/flipper-zero?variant=42927883452646")
    html = r.text
    p = LinksParser_lab401()
    p.feed(html)
    if ("Basic - Sold Out" not in "".join(p.data)):
        return False
    if ("Standard - Sold Out" not in "".join(p.data)):
        return False
    if ("Complete - Sold Out" not in "".join(p.data)):
        return False
    return True

def isFlipperZeroSoldOut3():
    r = requests.get("https://hackerwarehouse.com/product/flipper-zero/")
    html = r.text
    p = LinksParser_hackerwarehouse()
    p.feed(html)
    if (len(p.data) > 0):
        if ("In stock" in p.data[0]):
            return False
    return True

def post(content):
    m = Mastodon(access_token=TOKEN, api_base_url=SERVER_URL)
    a = m.status_post(status=content)

def main():
    while True:
        content = ""
        if (not isFlipperZeroSoldOut1()):
            content += "Flipper Zero currently in stock at https://shop.flipperzero.one/\n"
        if (not isFlipperZeroSoldOut2()):
            content += "Flipper Zero currently in stock at https://lab401.com/products/flipper-zero?variant=42927883452646\n"
        if (not isFlipperZeroSoldOut3()):
            content += "Flipper Zero currently in stock at https://hackerwarehouse.com/product/flipper-zero/\n"
        if (not isFlipperZeroDevBoardSoldOut1()):
            content += "Flipper Zero wifi dev board currently in stock at https://shop.flipperzero.one/products/wifi-devboard\n"
        if (not isFlipperZeroDevBoardSoldOut2()):
            content += "Flipper Zero wifi dev board currently in stock at https://lab401.com/products/flipper-zero-wifi-devboard?variant=42938105004262\n"
        if content:
            post(content)
        else:
            post("flipper zero and wifi dev board sold out at shop dot flipperzero, lab401, and hackerwarehouse")
        time.sleep(DELAY)

if __name__ == "__main__":
    main()
