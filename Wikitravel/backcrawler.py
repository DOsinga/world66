#!/usr/bin/env python

"""BackCrawler is a spider to explore web pages and save all background
image files to a directory. See the "savedir" variable below.

Note! there are two ways to stop the script. One is by pressing ^c (ctrl-c)
(you must then wait until the current url is fetched); the other is to to
create a file named "bc.kill" in the same directory as the script is in.
The script will detect the file and shut down before the next loop.

- duplicates are rejected based on MD5 fingerprint
- BackCrawler handles frames and "refresh" headers.
- BackCrawler is very inefficient and does everything in memory

Optionally the bc.kill file can contain the following directives
(if any directive is found the script will not shut down but follow
the instructions sequentially):
  filter: string     [ remove all URLs from Queue containing the string ]
  reduce: number     [ removes "number" percent random URL's from queue ]
  save               [ immediately save all lists to disk               ]
  kill               [ backcrawler should shut down -- use this last    ]

You can supply any number of starting URLs on the command line, and
also the following switches (which must precede any urls) are supported:

  -f string          - same as the "filter" command described above.
  -r number          - same as the "reduce" command described above.
  -s path            - the directory used to save downloaded images.

Warning! This script can be extremely slow.

by Tim Middleton (x@Vex.Net) - http://www.vex.net/~x/python_stuff.html

$Id: backcrawler.py,v 1.2 2001/07/21 17:17:58 x Exp $
"""

import os,sys,re,Queue,string,types,md5,whrandom,getopt
import httplib,urllib,urlparse


# initialise constants and variables
# savedir = "e:/xx"
savedir = "."                            # default to current directory

fnQueue = "bc_queue.bcl"                 # list of URLs to be visited
fnVisited = "bc_visited.bcl"             # list of visited URLs
fnBackgrounds = "bc_backgrounds.bcl"     # list of urls which denied access or other error
fnNoAccess = "bc_noaccess.bcl"           # list of background graphic urls
fnMD5 = "bc_md5.bcl"                     # list of MD5 fingerprints of all downloaded graphics
fnStats = "bc_stats.bcl"                 # save statistics between sessions
fnMsg = "bc.kill"                        # semaphor file to shut down or send messages

chrError = "!"
chrWarn = "|"
chrLoad = ">"
chrSave = "<"
chrScan = "*"
chrDupe = "@"
chrAdd  = "+"
chrMsg  = "="
chrDebug = "#"

maxVisitsBeforeSave = 60           # number of sites to visit before saving all lists
maxQueueSize = 26000               # maximum size to let the queue grow to
maxQueueSizeReduce = 30            # percentage to remove when queue too big

# here are some starting points if now initial URL is given.
start = [
        'http://antwrp.gsfc.nasa.gov/apod/astropix.html',
        'http://random.yahoo.com/bin/ryl',
        'http://dir.yahoo.com/new/',
        'http://www.random.com/all/',
        ]

# this is to track totals between sessions, but isn't implemented
stats = { 'total_kCrawled' : 0, 'total_bgBytes' : 0 }

# maybe someday
maxThread = 10
Threads = 0

visited = []            # list of visited URLs
noaccess = []           # list of urls which denied access or other error
backgrounds = []        # list of background graphic urls
md5s = []               # list of MD5 fingerprints of all downloaded graphics

# compile regular expressions
re_ads = re.compile(r"#|\?|/ad[-/]|/ads[^\w]|ublecl|adforc|cgi|/exec/|[-/]bin/|(amazon|netscape|microsoft|ibm|yahoo|excite)\.c|ocities.com/[^A-Z]")
re_badtypes = re.compile(r"\.(exe|zip|txt|pdf|gif|jpg|jpeg|png|hqx|gz|z|cgi|pl|ps|map|dvi|mov|avi|mp3|wav|mid|mpg)$",re.I)
re_background = re.compile(r'background\s*=\s*"(.*?)"',re.I)
re_href = re.compile(r'href\s*=\s*"(.*?)"',re.I)
re_framesrc = re.compile(r'<frame.*?src\s*=\s*"(.*?)"',re.I)
re_metarefresh = re.compile(r'URL=(.*?)"',re.I)

Q = Queue.Queue(0)

def prompt_user_passwd(self, host, realm):
    # to override urllib pausing for passwords
	return None, None

urllib.FancyURLopener.prompt_user_passwd = prompt_user_passwd

def reduceQueue(p,msg=""):
    "reduce the Queue loosing a certain percentage of random strings"
    if p<1 or p>99:
        if msg: print chrError+" invalid percentage (%s%%)" % p
        return
    global Q
    fcount = 0
    Q2 = Queue.Queue(0)
    while not Q.empty():
        tmp = Q.get()
        if whrandom.random()*100 > p:
            Q2.put(tmp)
        else:
            fcount = fcount + 1
    if msg: print msg % (fcount,p)         #
    Q = Q2

def randomiseQueue(Q):
    """Take all the items out of the Queue, put them back randomly"""
    print chrWarn + " randomising the Queue!"
    lst = []
    while not Q.empty():
        lst.append(Q.get())
    while lst:
        i = whrandom.randint(0, len(lst)-1)
        Q.put(lst[i])
        del lst[i]

def filterQueue(s,msg=""):
    "filter out all strings in Queue containing the given substring"
    global Q
    fcount = 0
    Q2 = Queue.Queue(0)
    while not Q.empty():
        tmp = Q.get()
        if string.find(tmp,s)>=0:
            fcount = fcount + 1
        else:
            Q2.put(tmp)
    Q = Q2
    if msg: print msg % (fcount,s)
    return fcount

def processMsg():
    "read the kill semaphor and see if it has any instructions to follow instead of shutting down"
    global visitcount
    keepon = 0
    try:
        f = open(fnMsg,'r')
        while 1:
            l = f.readline()
            if not l: break
            if string.find(l,'filter:')==0:
                filterQueue(string.strip(l[7:]),chrMsg+" Filtered %s URLs with '%s'.")
                keepon = 1
            if string.find(l,'reduce:')==0:
                reduceQueue(string.atoi(string.strip(l[7:])),chrMsg+" Dropped %s Urls (approx %s%% of Queue).")
                keepon = 1
            if string.find(l,'save')==0:
                print "Crawled %d bytes of HTML, and %d bytes of backgrounds." % (kCrawled,bgBytes)
                writeLists(1,0)
                visitcount=0
                keepon = 1
            if string.find(l,'kill')==0:
                keepon = 0
        f.close()
    except IOError:
        if f: f.close()
    return keepon

def readQueue(fnQueue,Q,msg=""):
    "read the given filename into the given Q, print optional summary at end"
    if os.path.exists(fnQueue):
        try:
            f = open(fnQueue,'r')
            while 1:
                i = f.readline()
                if not i: break
                Q.put(string.rstrip(i))
        except IOError:
            print chrError+" Error reading %s" % fnQueue
        f.close()
    if msg: print  msg % Q.qsize()
    return Q

def readMD5(fnMD5,lst,msg=""):
    "read the MD5 hash filename into the given list, print optional summary at end"
    lst = []
    if os.path.exists(fnMD5):
        try:
            f = open(fnMD5,'rb')
            s = f.read()
            if len(s) % 16:
                sys.stderr.write("%s Corrupt MD5 file! %s bytes is not divisible by 16!\n" % (chrError,len(s)))
                sys.exit(1)
            for x in range(0,len(s),16):
                lst.append(s[x:x+16])
        except IOError:
            print chrError+" Error reading %s" % fnMD5
        f.close()
    if msg: print msg % len(lst)
    return lst

def readList(fnList,lst,msg=""):
    "read the given filename into the given list, and optionally print a summary message"
    lst = []
    if os.path.exists(fnList):
        try:
            f = open(fnList,'r')
            while 1:
                i = f.readline()
                if not i: break
                lst.append(string.rstrip(i))
        except IOError:
            print chrError+" Error reading %s" % fnList
        f.close()
    if msg: print msg % len(lst)
    return lst

def readLists():
    "read the Q and all the lists"
    global Q,visited,backgrounds,md5s,noaccess
    md5s =        readMD5(fnMD5,md5s,chrLoad+" %s MD5 fingerprints loaded...")
    visited =     readList(fnVisited,visited,chrLoad+" %s Visited URLs loaded...")
    backgrounds = readList(fnBackgrounds,backgrounds,chrLoad+" %s Visited background URLs loaded...")
    noaccess =    readList(fnNoAccess,noaccess,chrLoad+" %s URLs with no access loaded...")
    Q =           readQueue(fnQueue,Q,chrLoad+" %s Queue items loaded...")


def writeList(fnList,lst,msg="",srt=1):
    "write list to text file, print optional message, optionally sort before writing"
    if msg: print msg % len(lst)
    if srt: lst.sort()
    try:
        qf = open(fnList,'w')
        for item in lst:
            if item:
                qf.write(item+"\n")
    except Exception:
        pass
    qf.close()

def writeMD5(fnMD5,lst,msg="",srt=1):
    "write MD5 list to hash (binary) file, print optional message, optionally sort before writing"
    s = ""
    if msg: print msg % len(lst)
    if srt: lst.sort()
    try:
        qf = open(fnMD5,'wb')
        for item in lst:
            s = s + item
        qf.write(s)
    except Exception:
        pass
    qf.close()

def writeQueue(fnQueue,Q,msg=""):
    "write Queue to text file, print optional message"
    if msg: print msg % Q.qsize()
    try:
        qf = open(fnQueue,'w')
        while not Q.empty():
            qf.write(Q.get()+"\n")
    except Exception:
        pass
    qf.close()

def writeStats():
    try:
        stats['total_kCrawled'] = stats['total_kCrawled'] + kCrawled
        stats['total_bgBytes'] = stats['total_bgBytes'] + bgBytes
        kCrawled = 0
        bgBytes = 0
        #pickle.dump(fnStats,stats)
    except Exception:
        pass

def writeLists(rereadQueue=0,srt=1):
    global Q
    writeMD5(fnMD5,md5s,chrSave+" writing MD5 fingerprint hash... %d items...")
    writeList(fnVisited,visited,chrSave+" writing visited list... %d items...",srt)
    writeList(fnBackgrounds,backgrounds,chrSave+" writing backgrounds list... %d items...",srt)
    writeList(fnNoAccess,noaccess,chrSave+" writing 'no access' list... %d items...",srt)
    writeQueue(fnQueue,Q,chrSave+" writing URL queue... %d items...")
    if rereadQueue:
        Q = readQueue(fnQueue,Q,chrLoad+" %s Queue items loaded...")

def msearch(pat,str,fl=0):
    """Return list of all regex matches in a string.

    Accepts either a string regex pattern (with optional flags) or
    a re object as the pattern"""
    ret = []
    lastpos = 0;
    if type(pat) == types.StringType:          # if it's a string compile it
        r = re.compile(pat,fl)
    else:
        r = pat                                 # assume it's an re object
    while 1:
        m = r.search(str,lastpos)
        if not m: break
        ret.append(m.groups()[0])
        lastpos = m.start()+1
    return ret

def getHREFs(s, url):
    """Get all http 'href' and 'frame src' from HTML string, return # found.

    s = HTML string to parse (ie. a web page)
    url = the source URL (so we can figure out relative URLs)
    """
    l = msearch(re_href,s,re.I)
    l = l + msearch(re_framesrc,s,re.I)
    l = l + msearch(re_metarefresh,s,re.I)
    if l:
        for x in range(len(l)):
            lx = urlparse.urljoin(url,l[x])
            if string.find(lx,'http://') >= 0:
                if not re_ads.search(lx):
                    #print "x",
                    if lx[-1]<>'/' and lx[-5]<>'.' and lx[-4]<>'.' and \
                            lx[-3]<>'.' and lx[-2]<>'.':
                        lx = lx + "/"
                    if lx not in visited:
                        if not re_badtypes.search(lx):
                            #print ",",
                            Q.put(lx)
                else:
                    pass
                    # print "! Bloody adverts."
    return len(l)

def getBG(s,u=None):
    """find the background names from an HTML file and make urls out of them

    s = HTML string (ie web page)
    u = source URL to figure out relative URLs
    """
    m = re_background.search(s)
    if not m: return ""
    bg = m.groups()[0]
    if u:
        bg = urlparse.urljoin(u,bg)
    return bg

def getFN(u,s):
    "return a new filename from URL to save graphic to"
    fn = ""
    num = 2
    i = string.rfind(u,'/')
    if i > -1:
        fn = savedir+u[i+1:]
        fp = os.path.splitext(fn)
        while os.path.exists(fn):
            fn = fp[0]+"_"+str(num)+fp[1]
            num = num + 1
        return fn
    return ""

def suckBG(u):
    "download the graphic, check for unique md5, save to unique filename"
    global bgBytes
    bget = None
    if u not in backgrounds:
            try:
                bget = urllib.urlopen(u)
                btmp = bget.read()
                if bget.info().getheader("Content-Type") == "text/html":
                    raise Exception
                bget.close()
            except Exception:
                if bget: bget.close()
                print chrError+" error getting background..."
                return
            md = md5.new(btmp).digest()
            if md not in md5s:
                md5s.append(md)
                fn = getFN(u,len(btmp))
                if fn:
                    fbg = open(fn,'wb')
                    fbg.write(btmp)
                    fbg.close()
                    bgBytes = bgBytes + len(btmp)
                    print chrSave+" Wrote %s (%d bytes)" % (fn,len(btmp))
            else:
                print chrDupe+" MD5 fingerprint for '%s' exists." % u[string.rfind(u,'/')+1:]


# ===================================================================
# ===================================================================

# if an arg on command line then push it into the Queue so it's first
try:
    opts, args = getopt.getopt(sys.argv[1:], 'f:hr:s:')
except getopt.error, msg:
    print msg
    sys.exit(1)

for arg in args:
    Q.put(arg)

for opt,optarg in opts:
    if opt == '-h':
        print "Read the comments at the top of this script file for help."
        print "Reading the documentation may or may not be helpful, also."
        sys.exit()
    if opt == '-f':
        slist = string.split(optarg,";")
        print "Filtering Queue",slist
        readLists()
        for s in slist:
            filterQueue(s,chrMsg+" Filtered %s URLs with '%s'.")
        writeLists()
        sys.exit()
    if opt == '-r':
        print "Reducing Queue"
        readLists()
        reduceQueue(string.atoi(optarg),chrMsg+" Dropped %s Urls (approx %s%% of Queue).")
        writeLists()
        sys.exit()
    if opt == '-s':
        savedir = optarg


if not os.path.exists(savedir):
    print "The 'savedir' (%s) does not exist." % savedir
    print "Please edit 'savedir=\"%s\"' line near the top of the script." % savdir
    sys.exit()

savedir = savedir + os.sep

readLists()

if Q.empty():
    for s in start:
        Q.put(s)

keepgoing = 1
visitcount = 0
kCrawled = 0
bgBytes = 0

try:
    os.remove(fnMsg)
except Exception:
    pass

try:
    while keepgoing and (not Q.empty()):
        if maxQueueSize and (Q.qsize() > maxQueueSize):
            reduceQueue(maxQueueSizeReduce,chrMsg+" Dropped %s Urls (approx %s%% of Queue).")
        if visitcount>maxVisitsBeforeSave:
            print "Crawled %d bytes of HTML, and %d bytes of backgrounds." % (kCrawled,bgBytes)
            writeLists(1,0)
            visitcount=0
            randomiseQueue(Q)
        url = Q.get_nowait()
        if url in visited:
            print chrWarn+" Already visited "+url+"."
            continue
        try:
            u = None
            print "%s Fetching %s {%d}" % (chrAdd,url,maxVisitsBeforeSave-visitcount)
            try:
                u = urllib.urlopen(url)
            except:
                raise IOError, "couldn't open"
            if u==None:
                raise IOError, "couldn't retrieve"
            try:
                contentType = u.info().getheader("Content-Type")
                if contentType <> "text/html":
                    raise IOError, "non-html: %s" % contentType
            except AttributeError,msg:
                raise IOError, "not responding?"
            f = u.read()
            u.close()
            kCrawled = kCrawled + len(f)
            hrefs = getHREFs(f, url)
            back = getBG(f,url)
            print chrScan+" %s links, background: '%s'." % (hrefs,back)
            if back and (back not in backgrounds):
                suckBG(back)
                backgrounds.append(back)
        except IOError,msg:
            print chrError+" Can't open %s (%s)" % (url,msg)
            noaccess.append(url)
            #if u: u.close()
        visited.append(url)
        if os.path.exists(fnMsg):
            keepgoing = processMsg()
            os.remove(fnMsg)
        visitcount = visitcount + 1


except KeyboardInterrupt:
    print chrMsg+" shutting down... %d urls in queue... " % Q.qsize()


writeLists()
print "Crawled %d bytes of HTML, and %d bytes of backgrounds." % (kCrawled,bgBytes)

