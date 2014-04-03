HTTPBenchmark
=============
HTTPBenchmark aims to be inbetween Apache Bench (ab) and a more full blown
HTTP test suite. In its simplest form it provides some basic compatibility with
ab in that it supports a -n switch to specify the number of requests to make
and a -c switch to specify how many concurrent users. 

However, the true intended use is to subclass HTTPBenchmark and to override the
``worker`` method to implement your own test logic. In this regard you can
think of HTTPBenchmark as a framework that allows you to build unit tests for
your HTTP application that aim to stress a server as well. See the Worker Code
section below.


Installation
------------
Installation is easily accomplished using ``pip`` or ``easy_install``.

.. code-block:: python

    pip install httpbenchmark


Basic Usage
-----------
A script named ``pb`` is provided and is intended to be a basic analog to the
Apache ``ab`` script.

.. code-block:: shell

    pb -n 1000 -c 25 http://my-host.tld/endpoint/


Worker code
-----------
By default HTTPBenchmark does nothing more than send a ``GET`` request and
expect a 200 OK return code. To fully utilize the system you should create
your own script that subclasses ``HTTPBenchmark``.

Here's an incomplete and untested example that is load testing some application
that deals with users and friends. It aims to illustrate the fundamentals of
using HTTPBenchmark

.. code-block:: python

    from httpbenchmark import HTTPBenchmark
    from tornado import gen
    import random

    USER_IDS = [1111, 2222, 3333, 4444]

    _url = lambda x: ''.join(['http://my-host.tld/', x])

    class MyBenchmark(HTTPBenchmark):
        @gen.coroutine
        def worker(self):
            '''
            get_worker should return a callable that will be called by the async http client
            '''
            if random.choice([True, False]):
                yield self.new_user()
            else:
                yield self.returning_user()

        @gen.coroutine
        def new_user(self):
            user_id = random.choice(USER_IDS)
            self.log.debug("New user: %s" % user_id)

            friends = yield self.open_json(_url("register?uid=%d" % user_id))
            # ... handle registration response ...
            if failure:
                self.log.error("Indicate reason for failure")
                self.log.debug("Show debugging info if you want")
                self.finish_request(False)
            else:
                yield self.next_step(user_id, friends['friendList'][0])

        @gen.coroutine
        def returning_user(self):
            user_id = random.choice(USER_IDS)
            self.log.debug("Returning user: %s" % user_id)

            def handle_login(response, friends):
            friends = yield self.open_json(_url("login?uid=%d" % user_id))
            # ... handle login response ...
            if failure:
                self.log.error("Indicate reason for failure")
                self.log.debug("Show debugging info if you want")
                self.finish_request(False)
            else:
                yield self.next_step(user_id, friends['friendList'][0])

        @gen.coroutine
        def next_step(self, user_id, friend_id):
            # ... do something else ...
            if failure:
                self.log.error("Indicate reason for failure")
                self.log.debug("Show debugging info if you want")
                self.finish_request(False)
            else:
                # success!
                self.finish_request()

    if __name__ == '__main__':
        MyBenchmark().main()


Essentials
^^^^^^^^^^

* This uses `Tornado's async generator interface`_ to achive concurrency, your
  functions need to be wrapped in ``@gen.coroutine`` and you should ``yield``
  between them.

* ``worker`` is where your main code lives. It will be called whenever there
  is a free slot based on concurrency.

* ``yield self.get(url, code=200)`` is used to make a GET request. You will
  get the response object back when the operation completes.

* ``self.post(url, params={}, callback)`` is used to POST data. ``params``
  should be a dictionary and will be sent as the POST data. It functions
  the same as ``get`` otherwise.

* If you're posting to a PHP backend and need to use PHP's neseted array
  syntax for parameters you pass ``php_urlencode`` to the ``self.post`` method
  with a value of ``True`` and it will encode the params accordingly.

* ``self.get_json(url, callback)`` is a shortcut for getting and parsing json
  data that is returned. Your callback should accept two arguments, the first
  is the response object and the second is the decoded json.

* ``self.finish_request(True/False)`` should be called to signal the end of a
  request. If everything worked as you expected pass it ``True``, otherwise
  pass it ``False``

* ``self.debug_response(response)`` is a handy function to use while you're
  developing your test cases. If you pass it a response object it will print
  out a summary of the object as well as the headers and body so you can debug
  the live data.

TODO
----

* Add some working examples

.. _Tornado's async generator interface: http://www.tornadoweb.org/en/stable/gen.html
