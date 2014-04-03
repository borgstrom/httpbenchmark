"""
HTTPBenchmark - a python based HTTP benchmarking & load testing tool

Copyright 2014 Evan Borgstrom

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import collections
import json
import logging
import numpy
import time
import urllib

from tornado import ioloop, httpclient, gen

from . import __version__


class HTTPBenchmark(object):
    """
    HTTPBenchmark aims to be inbetween Apache Bench (ab) and a more
    full blown HTTP test suite. In its simplest form* it provides some
    basic compatibility with ab in that it supports a -n switch to
    specify the number of requests to make and a -c switch to specify
    how many concurrent users. [*simplest form: HTTPBenchmark().main()]

    However, the true intended use is to subclass HTTPBenchmark and to
    override the get_worker method to implement your own test logic.

    This allows you to implement specific testing logic while being
    able to generate a modest load.

    At a concurrency of 100 I am able to generate ~1000 req/sec without
    breaking a sweat.
    """
    def __init__(self):
        # a dict of lists to store our results
        self.results = collections.defaultdict(list)

        # our logging object
        self.log = logging.getLogger("HTTPBenchmark")

        # use the curl async http client from tornado
        httpclient.AsyncHTTPClient.configure(
            "tornado.curl_httpclient.CurlAsyncHTTPClient"
        )

    def main(self):
        """
        Handles invocation
        """
        parser = argparse.ArgumentParser(
            description='pb - Python HTTP benchmarking tool'
        )

        # if our class is HTTPBenchmark then we expect that a URL
        # will be supplied to us as an argument, otherwise we have
        # been subclassed and it's expected that the object will
        # implement a custom get_worker() function
        if self.__class__.__name__ == 'HTTPBenchmark':
            parser.add_argument('url')

        # basic parameters
        parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                            help='Copious amounts of output')
        parser.add_argument('-v', '--version', action='version',
                            version='pb version {0}'.format(__version__),
                            help='Display the pb version and exit')

        # optional and mutually exclusive options
        modes = parser.add_mutually_exclusive_group()
        modes.add_argument('-n', '--number', dest='number', type=int,
                           metavar='NUMBER',
                           help='The total number of requests to make')
        modes.add_argument('-T', '--time', dest='time', type=int,
                           metavar='SECONDS',
                           help='The number of seconds to run at the '
                                'specified concurrency')

        # The main argument, how big our pool is
        parser.add_argument('-c', '--concurrent', dest='concurrent', type=int,
                            required=True,
                            help='The concurrent number of workers to spawn')

        self.args = parser.parse_args()

        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)s %(levelname)s '
                                       '%(message)s')
        else:
            logging.basicConfig(level=logging.INFO,
                                format='%(message)s')

        # now that we have our concurrency, create our client
        self.client = httpclient.AsyncHTTPClient()

        if self.args.number:
            return self.run_total()
        if self.args.time:
            return self.run_time()

        # bail out
        parser.print_help()

    def debug_response(self, response):
        """
        Function to dump response data for debugging purposes
        """
        print 'RESPONSE:'
        print 'CODE    :', response.code
        print 'TIME    :', response.request_time
        print 'URL     :', response.request.url

        headers = response.headers
        print 'HEADERS :'
        print '---------'
        print headers

        data = response.body
        print 'LENGTH  :', len(data)
        print 'DATA    :'
        print '---------'
        print data

    @gen.coroutine
    def worker(self):
        """
        The default worker - opens the URL.
        """
        self.open_url(self.args.url)
        self.finish_request()

    def finish_request(self, success=True):
        """
        Finishes a request started by open_url
        Set success to False if the request failed
        """
        if success:
            self.successful += 1
        else:
            self.failed += 1

        self.done += 1
        self.running -= 1

        # print a status every status_every percent
        percent = (self.done / float(self.args.number)) * 100
        if percent % self.status_every == 0:
            self.log.info("Completed %d requests" % self.done)

        # if we're done then stop our ioloop and finish the run
        if self.done == self.args.number:
            ioloop.IOLoop.instance().stop()
            self.finish_run()

    @gen.coroutine
    def open_url(self, url, code=200, params_in_results=False, **kwargs):
        """
        Opens a URL, recording the time it takes & return the response

        code is the HTTP status code that the request must return
        params_in_results controls if '/test' & '/test?1=2' should be
        stored in the results as the same item
        """
        response = yield self.client.fetch(url, **kwargs)

        # check if we need to strip params off the url before we store
        # the results
        if not params_in_results:
            url_params = url.find("?")
            if url_params > -1:
                url = url[:url_params]

        # store the results
        self.results[url].append(response.time_info)

        # ensure the status code is correct
        if response.code != code:
            self.finish_request(False)
        else:
            # otherwise "return" our response
            raise gen.Return(response)

    @gen.coroutine
    def get(self, url, code=200, params_in_results=False):
        response = yield self.open_url(
            url,
            code=code,
            params_in_results=params_in_results
        )
        raise gen.Return(response)

    @gen.coroutine
    def post(self, url, params={}, code=200, php_urlencode=False):
        if php_urlencode:
            body = self.php_urlencode(params)
        else:
            body = urllib.urlencode(params)

        response = yield self.open_url(
            url,
            code=code,
            method="POST",
            body=body
        )
        raise gen.Return(response)

    @gen.coroutine
    def get_json(self, url):
        response = yield self.open_url(url)

        # it should be json
        if response.headers.get('Content-Type') != 'application/json':
            self.debug_response(response)
            raise ValueError("Content-Type didn't match JSON")

        raise gen.Return(json.loads(response.body))

    def run_time(self):
        raise Exception("Sorry, this hasn't been implemented yet!")

    def run_total(self):
        self.log.info("Concurrency: %d" % self.args.concurrent)
        self.log.info("Total requests to be made: %d" % self.args.number)
        self.log.info("")

        self.start = time.time()
        self.done = 0
        self.successful = 0
        self.failed = 0
        self.running = 0

        self.status_every = 50
        if self.args.number >= 100:
            self.status_every = 20
        elif self.args.number >= 1000:
            self.status_every = 10
        elif self.args.number >= 10000:
            self.status_every = 5
        elif self.args.number >= 25000:
            self.status_every = 2.5

        loop = ioloop.IOLoop.instance()
        loop.add_callback(self.run_workers)
        loop.start()

    @gen.coroutine
    def run_workers(self):
        loop = ioloop.IOLoop.instance()

        if self.running < self.args.concurrent:
            # only start a new worker if doing so wont create more workers
            # than we need to complete our total
            if self.args.number - self.done > self.running:
                self.running += 1
                self.worker()

        loop.add_callback(self.run_workers)

    def finish_run(self):
        end = time.time()
        total_time = end - self.start
        req_sec = self.args.number / total_time

        self.log.info("Test took: {0} seconds".format(total_time))
        self.log.info("Successful requests: {0}".format(self.successful))
        self.log.info("Failed requests: {0}".format(self.failed))
        self.log.info("Number of HTTP requests: {0}".format(
            self.successful * len(self.results)))
        self.log.info("HTTP Requests per second: {0}".format(
            round(req_sec, 2)))
        self.log.info("")

        self.log.info("Summary:")

        for url in self.results:
            self.log.info(url)

            # each entry in the results for a url looks like
            # {'redirect': 0.0,
            #  'queue': 0.34013509750366211,
            #  'pretransfer': 0.0096919999999999992,
            #  'starttransfer': 0.020733000000000001,
            #  'connect': 0.0096810000000000004,
            #  'total': 0.020902,
            #  'namelookup': 3.1999999999999999e-05}

            times = [
                timing['total']
                for timing in self.results[url]
            ]

            self.log.info(" - Number of requests: {0}".format(
                len(self.results[url])))
            self.log.info(" - Average request: {0} sec".format(
                round(numpy.average(times), 2)))

            self.log.info(" - Completed request timing percentiles (ms)")

            pcts = [0, 50, 66, 75, 80, 90, 95, 98, 99, 100]
            avgs = numpy.percentile(times, pcts)
            for i in range(len(pcts)):
                self.log.info("   %3s%% %6s" % (pcts[i], int(avgs[i] * 1000)))

            self.log.info("")

    def php_urlencode(self, d):
        """
        URL-encode a multidimensional dictionary.
        """
        def recursion(d, base=[]):
            pairs = []

            for key, value in d.items():
                new_base = base + [key]
                if hasattr(value, 'values'):
                    pairs += recursion(value, new_base)
                else:
                    new_pair = None
                    if len(new_base) > 1:
                        first = urllib.quote(new_base.pop(0))
                        rest = map(lambda x: urllib.quote(x), new_base)
                        new_pair = "%s[%s]=%s" % (
                            first,
                            ']['.join(rest),
                            urllib.quote(unicode(value))
                        )
                    else:
                        new_pair = "%s=%s" % (
                            urllib.quote(unicode(key)),
                            urllib.quote(unicode(value))
                        )
                    pairs.append(new_pair)
            return pairs

        return '&'.join(recursion(d))
