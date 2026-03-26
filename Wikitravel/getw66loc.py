import sys
import urllib

from HTMLParser import HTMLParser

class AvgHTMLParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.in_title=0
        self.in_loc=0
        self.locid=0
        self.locname=""
        self.title=""
        self.locs=[]
        

    def handle_starttag(self, tag, attrs):
        if tag=='a':
            for prop,val in attrs:
                if prop=='href':
                    script,pars=val.split('?')
                    if script=='CityGuide.asp':
                        for par in pars.split('&'):
                            partag,parval=par.split('=')
                            if partag=='Loc':
                                self.locid=parval
                                self.locname=""
                                self.in_loc=1
        if tag=='title':
            self.in_title=1
            
    def handle_data(self,data):
        if self.in_title:
            self.title+=data
        if self.in_loc:
            self.locname+=data
       #print "Encountered the beginning of a %s tag" % tag

    def handle_endtag(self, tag):
        if tag=='title':
            self.in_title=0
        if tag=='a' and self.in_loc:
            if self.locname!='The World':
                self.locs+=[(self.locid,self.locname)]
                self.in_loc=0


while(1):
    locurl, locid = urllib.urlopen('http://localhost/World/unprocessedNode').read().split('@')
    if str(locid)=='0': break
    base_url="http://www.world66.com/devl/avantgo/CityGuide.asp?Loc=%s" % locid
    data = urllib.urlopen(base_url).read()
    parser=AvgHTMLParser()
    parser.feed(data)
    parser.close()
    
    print 'so far:'
    for id,name in parser.locs:
        data=urllib.urlopen( '%s/addChild?title=%s&locid=%s' % (locurl, urllib.quote(name), urllib.quote(id) ) ).read()
        print data
    data=urllib.urlopen( '%s/childrenready' % locurl ).read()
    print data