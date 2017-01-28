This is a little python app that can be used as a starting point
for delivering dump-job related data via api calls.

It is intended to be used with uwsgi.  It does not need any dump
code.  This is a deliberate choice; in the future it will not
need to know how to map dump job names to filenames, or to
construct paths for filenames for a dump on a given date.  All
of that will be done by the dump jobs themselves, and output
collected by the monitor in some reasonable format, which then
can be checked by this script.

Since job data collection methods are going to change, there
is a plugin architecture, with the possibility of multiple classes
doing different sorts of lookup.  The lookup implemented right now
scrapes dumpruninfo.txt, runsetttings.txt, md5sums.txt and sha1.txt
for each wiki, as well as doing a glob on certain files in the
directory for large wikis with multiple files per job.

The scraper implementation is only a proof of concept; it's not
efficient, nor is it meant to be.  The next piece of work should
be a patchset to the dumps to write some files in json in addition
to txt, and then to the monitor to collect information and write
it in a central file covering all wikis, in json format.

No comments in the code yet, that's poor. Meh.

No error handling: exceptions turn into empty message bodies.

Sample url (for my setup with my local MediaWiki installation
and wikis and dump runs and dates):

http://localhost/?wikis=elwikt&dates=20161207
