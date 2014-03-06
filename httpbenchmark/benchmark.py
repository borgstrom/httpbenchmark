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

import collections
import json
import logging
import numpy
import time
import urllib

from tornado import ioloop, httpclient

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
        httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

    def main(self):
        """
        Handles invocation
        """
        import argparse
        parser = argparse.ArgumentParser(description='pb - Python HTTP benchmarking tool')

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
                           help='The number of seconds to run at the specified concurrency')

        # The main argument, how big our pool is
        parser.add_argument('-c', '--concurrent', dest='concurrent', type=int,
                            required=True,
                            help='The concurrent number of workers to spawn')

        self.args = parser.parse_args()

        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)s %(levelname)s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO,
                                format='%(message)s')

        # now that we have our concurrency, create our client
        self.client = httpclient.AsyncHTTPClient(max_clients=self.args.concurrent)

        if self.args.number:
            return self.run_total()
        if self.args.time:
            return self.run_time()

        # bail out
        parser.print_help()

    def iscallable(self, inst):
        return hasattr(inst, '__call__') or isinstance(inst, collections.Callable)

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

    def get_worker(self):
        """
        Returns a callable that will be used by the worker
        """
        return self.default_worker

    def default_worker(self):
        """
        The default worker - opens the URL.
        """
        self.open_url(self.args.url)

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

        # print a status every status_every percent
        if ((self.done / float(self.args.number)) * 100) % self.status_every == 0:
            self.log.info("Completed %d requests" % self.done)

        # if we're done then stop our ioloop and finish the run
        if self.done == self.args.number:
            ioloop.IOLoop.instance().stop()
            self.finish_run()

    def open_url(self, url, callback=None, code=200, params_in_results=False, **kwargs):
        """
        Opens a URL, recording the time it takes & return the response

        code is the HTTP status code that the request must return
        params_in_results controls if '/test' & '/test?1=2' should be
        stored in the results as the same item
        """
        def handle_response(response):
            url = response.request.url

            # check if we need to strip params off the url before we store
            # the results
            url_params = url.find("?")
            if not params_in_results and url_params > -1:
                url = url[:url_params]

            # store the results
            self.results[url].append(response.time_info)

            # ensure the status code is correct
            if response.code != code:
                return self.finish_request(False)

            if self.iscallable(callback):
                # if we have another call back pass the response along
                return callback(response)
            else:
                # otherwise signal success
                return self.finish_request(True)

        self.client.fetch(url, handle_response, **kwargs)

    def get(self, url, callback=None, code=200, params_in_results=False):
        return self.open_url(url, callback, code, params_in_results)

    def post(self, url, params={}, callback=None, code=200):
        return self.open_url(url, callback, code,
                             method="POST",
                             body=urllib.urlencode(params))

    def get_json(self, url, callback):
        def handle_json(response):
            headers = response.headers

            # it should be json
            if "Content-Type" not in headers or \
                    headers["Content-Type"] != 'application/json':
                self.debug_response(response)
                raise ValueError("Content-Type didn't match JSON")

            try:
                callback(response, json.loads(response.body))
            except ValueError:
                self.debug_response(response)
                raise

        self.open_url(url, handle_json)

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

        self.status_every = 50
        if self.args.number >= 100:
            self.status_every = 20
        elif self.args.number >= 1000:
            self.status_every = 10
        elif self.args.number >= 10000:
            self.status_every = 5
        elif self.args.number >= 25000:
            self.status_every = 2.5

        for x in xrange(self.args.number):
            # get_worker will return a callable
            worker = self.get_worker()
            if self.iscallable(worker):
                try:
                    worker()
                except Exception, e:
                    self.log.error("worker raised an exception", e)
                    raise
            else:
                self.log.error("get_worker didn't return a valid callable object: {0}".format(
                    worker
                ))

        ioloop.IOLoop.instance().start()

    def finish_run(self):
        end = time.time()
        total_time = end - self.start

        self.log.info("Test took: {0} seconds".format(total_time))
        self.log.info("Successful requests: {0}".format(self.successful))
        self.log.info("Failed requests: {0}".format(self.failed))
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

            times = [t['total'] for t in self.results[url]]

            req_sec = len(self.results[url]) / total_time

            self.log.info(" - Number of requests: {0}".format(len(self.results[url])))
            self.log.info(" - Average request: {0} sec".format(round(numpy.average(times), 2)))
            self.log.info(" - Total time spent: {0} sec".format(round(total_time, 2)))
            self.log.info(" - Requests per second: {0}".format(round(req_sec, 2)))

            self.log.info(" - Completed request timing percentiles (ms)")

            pcts = [0, 50, 66, 75, 80, 90, 95, 98, 99, 100]
            avgs = numpy.percentile(times, pcts)
            for i in range(len(pcts)):
                self.log.info("   %3s%% %6s" % (pcts[i], int(avgs[i] * 1000)))

            self.log.info("")
