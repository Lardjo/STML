#!/usr/bin/env python3

import logging

from motor import Op
from tornado.gen import coroutine, Wait, Callback
from tornado.escape import json_decode
from tornado.httputil import url_concat
from tornado.httpclient import AsyncHTTPClient
from datetime import datetime


@coroutine
def update_match(db, match_id):
    if match_id is None:
        logging.debug("No new match for update")
        return
    match = yield Op(db['matches'].find_one, {'match_id': match_id})
    if match:
        logging.info('Match already in database. Pass')
        return
    key = yield Op(db["server"].find_one, {"key": "apikey"})
    url = url_concat("http://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/",
                     {"match_id": match_id, "key": key["value"]})
    http_client = AsyncHTTPClient()
    http_client.fetch(url, callback=(yield Callback("match_key")))
    response = yield Wait("match_key")
    if response.error:
        logging.warning("Match #%s not updated. Remote server not respond" % match_id)
        db["status"].update({"status": "api_dota"}, {"$set": {"value": "false", "time": datetime.now()}}, w=1)
    else:
        array = json_decode(response.body)['result']
        for pl in array['players']:
            items = [pl['item_0'], pl['item_1'], pl['item_2'], pl['item_3'], pl['item_4'], pl['item_5']]
            pl['items'] = items
        yield Op(db['matches'].insert, array)
        db['status'].update({'status': 'api_dota'}, {'$set': {'value': 'true', 'time': datetime.now()}}, w=1)
        logging.info('Match #%s added to database' % match_id)