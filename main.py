import os
import logging
import webapp2
import urlparse
import urllib
import httplib2
import urllib2
import logging
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

try:
    import json
except ImportError:
    import simplejson as json


RESOURCE_URL = '%(protocol)s://%(user)s.%(domain)s/api/%(api_version)s/sql'

class CartoDB(object):
    """ basic client to access cartodb api """
    MAX_GET_QUERY_LEN = 2048

    def __init__(self, cartodb_domain, host='cartodb.com', protocol='https', api_version='v2'):
        self.resource_url = RESOURCE_URL % {'user': cartodb_domain, 'domain': host, 'protocol': protocol, 'api_version': api_version}
        self.client = httplib2.Http()
    def req(self, url, http_method="GET", http_headers={}, body=''):
        """
        this method should implement how to send a request to server using propper auth
        """
        if http_method == "POST":
            body = body
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            # headers.update(http_headers)
            resp, content = self.client.request(url, "POST", body=body, headers=headers)
        else:
            url = url
            resp, content = self.client.request(url, headers=http_headers)
        
        return resp, content

    def sql(self, sql, parse_json=True, do_post=True):
        """ executes sql in cartodb server
            set parse_json to False if you want raw reponse
        """
        p = urllib.urlencode({'q': sql})
        url = self.resource_url
        # depending on query size do a POST or GET
        if len(sql) < self.MAX_GET_QUERY_LEN and not do_post:
            url = url + '?' + p
            resp, content = self.req(url);
        else:
            resp, content = self.req(url, http_method='POST', body=p);

        if resp['status'] == '200':
            if parse_json:
                return json.loads(content)
            return content
        elif resp['status'] == '400':
            raise CartoDBException(json.loads(content)['error'])
        elif resp['status'] == '500':
            raise CartoDBException('internal server error')

        return None

class TableStream(object):
    def latest(self):
        lastrow = self.cdb.sql("select to_char(updated_at AT TIME ZONE 'UTC', 'Dy, DD Mon YYYY HH24:MI:SS UTC') updated_at from "+self.table_name+" order by updated_at desc limit 1")
        try: val = lastrow['rows'][0]['updated_at']
        except: val = None
        return val
    def __init__(self, user_name, table_name):
        self.cdb = CartoDB(user_name)
        self.user_name = user_name
        self.table_name = table_name
        knownitem = memcache.get('%s/%s/lastitem' % (self.table_name, self.user_name))
        self.latestitem = self.latest()
        if knownitem != self.latestitem:
            self.refresh = True
        else:
            self.refresh = False
    def data(self):
        memcache.set('%s/%s/lastitem' % (self.table_name, self.user_name), self.latestitem)
        if self.refresh:
            logging.error('refreshed')
            data = self.cdb.sql("select *, ST_AsText(the_geom) as geom, GeometryType(the_geom) as geom_type, null as the_geom_webmercator, null as the_geom, ST_X(ST_Centroid(the_geom)) as lon, ST_Y(ST_Centroid(the_geom)) as lat from %s order by updated_at desc LIMIT 100" % self.table_name)
            memcache.set('%s/%s/data' % (self.table_name, self.user_name), data)
        else:
            logging.error('cached')
            data = memcache.get('%s/%s/data' % (self.table_name, self.user_name))
            if data is None:
                data = {"rows": []}
                memcache.set('%s/%s/data' % (self.table_name, self.user_name), data)
        return data, self.latestitem


class GeoRSS(webapp2.RequestHandler):
    def get(self, user_name, table_name):
        stream = TableStream(user_name, table_name)
        data, latest = stream.data()
        
        template_values = {'user_name': user_name, 'table_name': table_name,
                           'rows': data['rows'], 'latest': latest}
        dispatch = 'templates/georss.html'
        path = os.path.join(os.path.dirname(__file__), dispatch)
        output = template.render(path, template_values)
        self.response.headers['Cache-Control'] = 'public,max-age=%s' \
            % 86400
        # 'Content-Type: text/xml'
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(unicode(output))

app = webapp2.WSGIApplication([ 
        ('/([^/]+)/([^/]+)/feed.xml', GeoRSS) 
    ], debug=True)

