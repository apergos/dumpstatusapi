import sys
import os
sys.path.append(os.path.dirname(__file__))
from urlparse import parse_qs
from utils import Config, WikiList
from wiki_info_factory import WikiInfoFactory


def get_wikis_dates_todo(parameters, conf):
    wiki_retriever = WikiList(conf['wikilists'])
    all_wikis = wiki_retriever.get_all_wikis(conf['skip'], conf['allwikis'])

    if 'wikis' in parameters:
        wikis_todo = [wikiname.strip() for wikiname in parameters['wikis']]
        wikis_todo = [wikiname for wikiname in wikis_todo if wikiname in all_wikis]
    else:
        wikis_todo = all_wikis

    if 'dates' in parameters:
        dates_todo = [dates.strip() for dates in parameters['dates']]
    else:
        dates_todo = ['latest']
    return wikis_todo, dates_todo


def application(env, start_response):
    try:
        config_retriever = Config("/srv/dumpstatus/dumpstatus.conf")
        conf = config_retriever.get_config()

        parameters = parse_qs(env.get('QUERY_STRING', ''))
        # parameters = parse_qs("wikis=elwikt&dates=20161207", '')

        wikis_todo, dates_todo = get_wikis_dates_todo(parameters, conf)

        backend_chooser = WikiInfoFactory(conf['dumpsdir'])
        wiki_info_retriever = backend_chooser.get(conf['backend'])
        wiki_entries = [wiki_info_retriever.get_wiki_info(wiki, dates_todo) for wiki in wikis_todo]

        body = '\n'.join(wiki_entries)
        start_response('200 OK', [('Content-Type', 'application/json')])
        return[body]
    except:
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return["The dumps API application ran into problems. "
               "Please check your parameters and try again."]


if __name__ == "__main__":
    print application(None, None)
