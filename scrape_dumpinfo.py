import os
import json
from collections import OrderedDict
from utils import DumpDir, DumpFile


class DumpRunInfo(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    def get_dumpruninfo(self, wiki, date):
        dumpfile_retriever = DumpFile(self.dumpsdir)
        lines = dumpfile_retriever.get_dumpfile_content(wiki, date, "dumpruninfo.txt")
        return lines

    def get_jobs_from_dumpruninfo(self, wiki, date):
        entries = self.get_dumpruninfo(wiki, date)
        if entries is None:
            return None
        jobs = []
        for entry in entries:
            # these jobs would eventually be a list of
            # {name: jobname, status: done, started: sometime, completed: sometime}

            # the input is a series of lines like:
            # name:metacurrentdumprecombine; status:done; updated:2016-12-07 21:00:27
            fields = entry.split(';')
            fields = [field.strip() for field in fields]
            job = OrderedDict()
            job['name'] = fields[0].split(':', 1)[1]
            job['status'] = fields[1].split(':', 1)[1]
            job['updated'] = fields[2].split(':', 1)[1]
            # no 'completed' or 'started' yet because they aren't available anywhere
            jobs.append(job)
        return jobs

    def get_runsettings_info(self, wiki, date):
        if date == 'latest':
            dumpdir_retriever = DumpDir(self.dumpsdir)
            date = dumpdir_retriever.get_latest_date(wiki)
        dumpfile_retriever = DumpFile(self.dumpsdir)
        lines = dumpfile_retriever.get_dumpfile_content(
            wiki, date, DumpFile.get_dumpfile_name(wiki, date, "runsettings.txt"))
        lines = [line for line in lines if line.strip() and not line.startswith('#')]
        if len(lines) != 1:
            return None
        # [1, "1000,1000,1000,1000", "", "3", "100000", 1, 1]
        # parts, pages_per-filepart_history, parts_for_abstract, recombine_history, checkpoint
        runsettings = {}
        fields = lines[0].split()

        if fields[0]:
            runsettings['parts'] = True
        if fields[1]:
            runsettings['historyparts'] = len(fields[1].rstrip(',').split(','))
        if fields[3]:
            runsettings['abstractparts'] = int(fields[3].rstrip(',').strip('"'))
        if fields[5]:
            runsettings['recombine'] = True
        if fields[6]:
            runsettings['checkpoints'] = True
        return runsettings


class HashInfo(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    def get_hashinfo(self, wiki, date, hashtype):
        # elwikt-20161207-<hashtype>.txt
        if date == 'latest':
            dumpdir_retriever = DumpDir(self.dumpsdir)
            date = dumpdir_retriever.get_latest_date(wiki)
        dumpfile_retriever = DumpFile(self.dumpsdir)
        lines = dumpfile_retriever.get_dumpfile_content(
            wiki, date, DumpFile.get_dumpfile_name(wiki, date, hashtype + ".txt"))
        # 90223f748898280921b58ec36c100cbf  elwikt-20161207-abstract.xml
        hashes = {}
        for line in lines:
            hashinfo, filename = line.split()
            hashes[filename] = hashinfo
        return hashes

    def get_md5info(self, wiki, date):
        return self.get_hashinfo(wiki, date, "md5sums")

    def get_sha1info(self, wiki, date):
        return self.get_hashinfo(wiki, date, "sha1sums")


class JobFiles(object):
    # note that it's safe to put recombine jobs here,
    # even though not all wikis run them.  if it's in
    # the dumpruninfo file, then it's set to run for that wiki.
    JOBGLOBS = {
        'metahistory7zdump': ['pages-meta-history{num}.xml.7z'],
        'metahistorybz2dump': ['pages-meta-history{num}.xml.bz2'],
        'metacurrentdump': ['pages-meta-current{num}.xml.bz2'],
        'articlesdump': ['pages-articles{num}.xml.bz2'],
        'xmlstubsdump': [
            'stub-articles{num}.xml.gz',
            'stub-meta-current{num}.xml.gz',
            'stub-meta-history{num}.xml.gz'
        ],
        'abstractsdump': ["abstract{num}.xml"],
        'articlesmultistreamdump': [
            'pages-articles-multistream-index.txt.bz2',
            'pages-articles-multistream.xml.bz2'
        ],
        'xmlpagelogsdump': ["pages-logging.xml.gz"],
        'allpagetitlesdump': ["all-titles-in-ns0.gz"],
        'pagetitlesdump': ["all-titles.gz"]
    }

    JOBTABLES = {
        'changetags': 'change_tag',
        'pageprops': 'page_props',
        'pagerestrictions': 'page_restrictions',
        'protectedtitles': 'protected_titles',
        'sitestats': 'site_stats',
        'usergroups': 'user_groups',
        'geotags': 'geo_tags'
    }

    JOBCHKPTS = {
        'metahistory7zdump': ['pages-meta-history{num}.xml-p*p*.7z'],
        'metahistorybz2dump': ['pages-meta-history{num}.xml-p*p*.bz2']
    }

    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    @staticmethod
    def get_files_for_table_job(wiki, date, jobname):
        tablename = jobname[0:-5]
        if tablename in JobFiles.JOBTABLES:
            tablename = JobFiles.JOBTABLES[tablename]

        filename = DumpFile.get_dumpfile_name(wiki, date, tablename + ".sql.gz")
        return [filename]

    @staticmethod
    def get_files_for_easy_cases(wiki, date, jobname):
        if jobname.endswith("recombine"):
            jobname = jobname[0:-9]

        if jobname not in JobFiles.JOBGLOBS:
            return None
        else:
            return [DumpFile.get_dumpfile_name(wiki, date, filename.format(num=''))
                    for filename in JobFiles.JOBGLOBS[jobname]]

    def get_parts_chkpts(self, wiki, date, jobname):
        dumpruninfo_retriever = DumpRunInfo(self.dumpsdir)
        runsettings = dumpruninfo_retriever.get_runsettings_info(wiki, date)

        checkpoints = bool('checkpoints' in runsettings and
                           jobname.startswith('metahistory') and
                           not jobname.endswith("recombine"))

        partscount = 0
        if 'parts' not in runsettings or jobname.endswith("recombine"):
            return partscount, checkpoints

        if jobname.startswith("abstract"):
            partscount = runsettings['abstractparts']
        if jobname in JobFiles.JOBGLOBS:
            # if one name in the list takes partnums,
            # they all do
            if '{num}' in JobFiles.JOBGLOBS[jobname][0]:
                partscount = runsettings['historyparts']

        return partscount, checkpoints

    def get_files_for_hard_cases(self, wiki, date, jobname, partscount, chkpts):
        # these are the harder cases
        if chkpts and jobname.startswith('metahistory'):
            # no idea what files are there, must glob
            if jobname not in JobFiles.JOBCHKPTS:
                return []
            to_glob = [DumpFile.get_dumpfile_name(wiki, date, filename.format(num=str(n)))
                       for n in range(1, partscount+1)
                       for filename in JobFiles.JOBCHKPTS[jobname]]
            dumpdir_retriever = DumpDir(self.dumpsdir)
            return dumpdir_retriever.find_matching_files(wiki, date, to_glob)

        elif not partscount:
            # one output file for content dumps, 3 for stubs
            return JobFiles.get_files_for_easy_cases(wiki, date, jobname)

        # sequence of numbered output files
        if jobname not in JobFiles.JOBGLOBS:
            return []
        return [DumpFile.get_dumpfile_name(wiki, date, filename.format(num=str(n)))
                for n in range(1, partscount+1)
                for filename in JobFiles.JOBGLOBS[jobname]]

    def get_files_for_job(self, wiki, date, jobname):
        # job name as it appears in the dumpruninfo file...
        if jobname.endswith('table'):
            return JobFiles.get_files_for_table_job(wiki, date, jobname)

        partscount, chkpts = self.get_parts_chkpts(wiki, date, jobname)
        if not partscount and not chkpts:
            files = JobFiles.get_files_for_easy_cases(wiki, date, jobname)
            if files:
                return files
            elif files is None:
                return []

        files = self.get_files_for_hard_cases(wiki, date, jobname, partscount, chkpts)
        if files:
            return files
        elif files is None:
            return []

    def get_filesizes(self, wiki, date, files):
        files = OrderedDict()
        dumpfile_retriever = DumpFile(self.dumpsdir)
        for file_info in files:
            path = dumpfile_retriever.get_dumpfile_path(wiki, date, file_info['name'])
            try:
                size = os.path.getsize(path)
            except Exception:
                continue
            # return size in bytes, no pretty printing
            file_info['size'] = size
        return files


class WikiInfo(object):
    def __init__(self, dumpsdir):
        self.dumpsdir = dumpsdir

    def get_wiki_info_per_date(self, wiki, date):
        # this should take various backends. we get the info by...?
        # for now we get from dumpruninfo and md5/sha files

        # produce: {job: name, status: in-progress/etc,
        # files: {name:something, size:something, md5sum: something, sha1:something}}
        dumpruninfo_retriever = DumpRunInfo(self.dumpsdir)
        jobs = dumpruninfo_retriever.get_jobs_from_dumpruninfo(wiki, date)

        hash_retriever = HashInfo(self.dumpsdir)
        md5info = hash_retriever.get_md5info(wiki, date)
        sha1info = hash_retriever.get_sha1info(wiki, date)

        jobfiles_retriever = JobFiles(self.dumpsdir)
        for job in jobs:
            # these jobs are a list of
            # {name: jobname, status: done, started: sometime, completed: sometime}
            files_per_job = jobfiles_retriever.get_files_for_job(wiki, date, job['name'])
            filesizes = jobfiles_retriever.get_filesizes(wiki, date, files_per_job)
            job['files'] = []
            for filename in files_per_job:
                # these files are a list of
                # {name: filename, size: bytes, md5sum: hash, sha1sum: hash}
                file_entry = OrderedDict()
                file_entry['name'] = filename
                if filename in filesizes:
                    file_entry['size'] = filesizes[filename]
                if filename in md5info:
                    file_entry['md5sum'] = md5info[filename]
                if filename in sha1info:
                    file_entry['sha1sum'] = sha1info[filename]
                job['files'].append(file_entry)
        return jobs

    def get_wiki_info(self, wiki_name, dates):
        entry = {}
        entry[wiki_name] = {}
        for date in dates:
            entry[wiki_name][date] = self.get_wiki_info_per_date(wiki_name, date)

        for date in entry[wiki_name].keys():
            if date is None:
                del entry[wiki_name][date]

        entry_json = json.dumps(entry)
        return entry_json
