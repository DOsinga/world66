import urllib, string
from urllib import urlencode

from HTMLParser import HTMLParser


def processLocation( baseUrl, data ):
    sections=data.split('*Section:')
    del sections[0]
    
    print 'found %d sections' % len(sections)

    for sec in sections:
        pois=sec.split('*Detail:')
        secbody=pois[0]
        del pois[0]
        
        secbody=secbody.split('\n')
        title=secbody[0].strip()
        del secbody[0]
        secbody=filter( lambda l: (len(l)<2) or (l[:2]!='--'), secbody)
        secbody='\n'.join(secbody)
        addsecurl='%s/addsectionChild?%s' % (baseUrl, urlencode( {'title':title, 'body':secbody}))
        print 'section created '+title
        res=urllib.urlopen(addsecurl).read()
        if res[:4]=='url=':
            dummy, sectionurl = res.split('=')
            for poitxt in pois:
                reviews = poitxt.split( 'Review' )
                poi=reviews[0]
                del reviews[0]
                poi=poi.split('\n')
                ptitle=poi.pop(0)
                p=ptitle.find(':')
                if p==-1:
                    ptype=''
                else:
                    ptype=ptitle[0:p]
                    ptitle=ptitle[p+1:]
                props={}
                props['title']=ptitle
                props['type']=ptype
                props['body']=''
                for l in poi:
                    if len(l)>0:
                        if l[0]=='.':
                            l=l[1:]
                            print '>>'+l
                            p=l.find('=')
                            if p>-1:
                                tag=l[:p]
                                val=l[p+1:]
                                props[tag]=val
                        else:
                            props['body']=props['body']+'\n'+l
                addpoiurl='%s/addChild?%s' % (sectionurl, urlencode(props))
                
                print urllib.urlopen(addpoiurl).read()
        else:
            print res

class LocEditParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.in_body=0
        self.body=""
        

    def handle_starttag(self, tag, attrs):
        if tag=='textarea' and self.body=='':
            self.in_body=1
            
    def handle_data(self,data):
        if self.in_body:
            self.body+=data
 
    def handle_endtag(self, tag):
        if tag=='textarea':
            self.in_body=0

def importWorld():
    agent = urllib.URLopener()

    d = {
        'email':  'dmo@oberon.nl',
        'password': 'odi et amo',
        'EditorLogin': 'Submit'
    }




    # get a session object denoted by a cookie
    print 'requesting session id'
    u = agent.open('http://www.world66.com/devl/login.asp')
    cookie= u.info()['set-cookie']
    cookie = cookie[:string.find(cookie, ';')]

    print 'loggin in at world66'
    # now login. w66 will throw a redirect exception
    agent.addheader('Cookie', cookie)
    try:
        u = agent.open('http://www.world66.com/devl/login.asp',
                       urllib.urlencode(d))
    except:
        a=1


    while(1):
        print 'retrieving next location'
        locurl, locid = urllib.urlopen('http://world66.oberon.nl/unprocessedSection').read().split('@')
        if str(locid)=='0': break

        print '**************************************************************'
        print 'retrieving information for %s' % locurl
        print '**************************************************************'

        locid=4
        u = agent.open('http://www.world66.com/editor/dumplocinfo.asp?loc=%s' % locid)
        data=u.read()

        f = open( r"C:\tmp\amsterdam.txt", "w" )
        f.write( data )
        f.close
        print "data written."
        break

        processLocation( locurl, data )    
        break
        print urllib.urlopen( '%s/sectionsready' % locurl ).read()


def test():
    f = open( r"C:\tmp\amsterdam.txt" )
    processLocation( 'http://world66.oberon.nl/World/Europe/Netherlands/Amsterdam', f.read() )
    f.close()

test()    