from app.config.cplog import CPLog
from app.lib.provider.yarr.base import nzbBase
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time
import traceback
from urllib import quote_plus

log = CPLog(__name__)

class nzbindex(nzbBase):
    """Api for nzbindex"""

    name = 'nzbindex.com'
    #downloadUrl = 'https://nzbs.org/index.php?action=getnzb&nzbid=%s%s'
    #nfoUrl = 'https://nzbs.org/index.php?action=view&nzbid=%s&nfo=1'
    #detailUrl = 'https://nzbs.org/index.php?action=view&nzbid=%s'
    searchUrl = 'http://www.nzbindex.com/rss/?q=%s&age=700&sort=agedesc&minsize=1000&max=250'
    
    timeBetween = 3 # Seconds

    def __init__(self, config):
        log.info('Using NzbIndex.com provider')

        self.config = config

    def conf(self, option):
        return self.config.get('NZBIndexCom', option)

    def enabled(self):
        return self.conf('enabled') and self.config.get('NZB', 'enabled')

    def find(self, movie, quality, type, retry = False):

        self.cleanCache();

        results = []
        
        url = self.searchUrl % quote_plus(self.toSearchString(movie.name + ' ' + quality))
        log.info('Searching: %s' % url)
        cacheId = str(movie.name + ' ' + quality)
        
        try:
            cached = False
            if(self.cache.get(cacheId)):
                data = True
                cached = True
                log.info('Getting RSS from cache: %s.' % cacheId)
            else:
                log.info('Searching: %s' % url)
                data = self.urlopen(url)
                self.cache[cacheId] = {
                    'time': time.time()
                }
        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        if data:
            log.debug('Parsing nzbindex.com RSS.')
            try:
                try:
                    if cached:
                        xml = self.cache[cacheId]['xml']
                    else:
                        xml = self.getItems(data)
                        self.cache[cacheId]['xml'] = xml
                except:
                    if retry == False:
                        log.error('No valid xml, to many requests? Try again in 15sec.')
                        time.sleep(15)
                        return self.find(movie, quality, type, retry = True)
                    else:
                        log.error('Failed again.. disable %s for 15min.' % self.name)
                        self.available = False
                        return results
                
            except:
                log.error('Failed to parse XML response from NZBs.org: %s' % traceback.format_exc())
                return False
                
            for nzb in xml:
                new = self.feedItem()
                
                id = self.gettextelement(nzb, "link").split('/')[4]
                date = self.gettextelement(nzb, "pubDate")
                description = self.gettextelement(nzb, "description")
                
                size = 9999
                for entry in description.split('\n'):
                    if entry.endswith('GB</b><br />') or entry.endswith('MB</b><br />'):
                        entry = entry[:-len("</b><br />")]
                        if entry.startswith('<b>'):
                          entry = entry[len("<b>"):]
                          size = self.parseSize(entry)
                
                new.id = id
                new.name = self.toSaveString(self.gettextelement(nzb, "title"))
                new.size = size
                new.content = self.gettextelement(nzb, "description")
                new.type = 'nzb'
                new.url = self.gettextelement(nzb, "link")
                new.date = int(time.mktime(parse(date).timetuple()))
                new.score = self.calcScore(new, movie)
                new.checkNZB = True
                
                
                #if self.isCorrectMovie(new, movie, type, imdbResults = True):
                #    results.append(new)
                #    log.info('Found: %s' % new.name)

        return results

