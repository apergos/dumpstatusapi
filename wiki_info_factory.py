import scrape_dumpinfo


class WikiInfoFactory(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    def get(self, name):
        if name == 'scraper':
            return scrape_dumpinfo.WikiInfo(self.dumpsdir)
        else:
            return None
