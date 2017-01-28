import os
import re
import glob
import ConfigParser


class WikiList(object):
    def __init__(self, basedir):
        self.basedir = basedir

    @staticmethod
    def read_entries(path):
        infile = open(path)
        entries = []
        for line in infile:
            line = line.strip()
            if line != "" and not line.startswith('#'):
                entries.append(line)
        infile.close()
        entries = sorted(entries)
        return entries

    def get_wikis(self, wikis_file):
        path = os.path.join(self.basedir, wikis_file)
        wikis = []
        if not os.path.exists(path):
            return wikis
        return WikiList.read_entries(path)

    def get_all_wikis(self, skip, allwikisfile):
        to_skip = []
        if skip is not None:
            skip = skip.split(',')
            for wikis_file in skip:
                more_skip = self.get_wikis(wikis_file)
                if not more_skip:
                    # if it was intended to skip some wikis and
                    # we could not get part or all of the list,
                    # bail rather than leaking possibly private info
                    raise ValueError("file of wikis to skip apparently "
                                     "empty or unreadable, bailing")
                to_skip.extend(more_skip)
        all_wikis = self.get_wikis(allwikisfile)
        all_wikis = [wikiname for wikiname in all_wikis if wikiname not in to_skip]
        return all_wikis


class DumpFile(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    @staticmethod
    def get_dumpfile_name(wiki, date, basename):
        return wiki + "-" + date + "-" + basename

    def get_dumpfile_path(self, wiki, date, filename):
        if date == 'latest':
            dumpdir_retriever = DumpDir(self.dumpsdir)
            date = dumpdir_retriever.get_latest_date(wiki)
        if date is None:
            return None
        path = os.path.join(self.dumpsdir, wiki, date, filename)
        if not os.path.exists(path):
            return None
        return path

    def get_dumpfile_content(self, wiki, date, filename):
        path = self.get_dumpfile_path(wiki, date, filename)
        try:
            with open(path, "r") as fdesc:
                lines = fdesc.read().splitlines()
            return lines
        except Exception:
            return None


class DumpDir(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    def get_latest_date(self, wiki):
        # find out what 'latest' means for this wiki. that means
        # the most recent run by yyyymmdd directory name, nothing else.
        digits = re.compile(r"^\d{4}\d{2}\d{2}$")
        dates = []
        try:
            for dirname in os.listdir(os.path.join(self.dumpsdir, wiki)):
                if digits.match(dirname):
                    dates.append(dirname)
        except OSError as ex:
            return None
        dates = dates.reverse()
        return dates[0]

    def find_matching_files(self, wiki, date, to_glob):
        files = []
        for globme in to_glob:
            files.extend(glob.glob(os.path.join(self.dumpsdir, wiki, date, globme)))
        return files


class Config(object):
    def __init__(self, config_file):
        self.config_file = config_file

    def get_config(self):
        parser = ConfigParser.SafeConfigParser()
        parser.readfp(open(self.config_file, "rb"))

        if not parser.has_section("directories"):
            raise LookupError("The mandatory configuration section 'directories' was not defined.")

        if not parser.has_option("directories", "wikilists"):
            raise LookupError("The mandatory setting 'wikilists' in the "
                              "section 'directories' was not defined.")
        if not parser.has_option("directories", "dumps"):
            raise LookupError("The mandatory setting 'dumps' in the section: "
                              "'directories' was not defined.")

        if not parser.has_section("misc"):
            raise LookupError("The mandatory configuration section 'misc' was not defined.")
        if not parser.has_option("misc", "backend"):
            raise LookupError("The mandatory setting 'backend' in the section: "
                              "'misc' was not defined.")

        conf = {}
        conf['wikilists'] = parser.get("directories", "wikilists")
        conf['dumpsdir'] = parser.get("directories", "dumps")
        conf['skip'] = None
        if parser.has_option("misc", "skip"):
            conf['skip'] = parser.get("misc", "skip")
        if parser.has_option("misc", "allwikis"):
            conf['allwikis'] = parser.get("misc", "allwikis")
        conf['backend'] = parser.get("misc", "backend")
        return conf
