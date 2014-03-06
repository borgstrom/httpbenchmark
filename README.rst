HTTPBenchmark
=============
HTTPBenchmark aims to be inbetween Apache Bench (ab) and a more full blown
HTTP test suite. In its simplest form it provides some basic compatibility with
ab in that it supports a -n switch to specify the number of requests to make
and a -c switch to specify how many concurrent users. 

However, the true intended use is to subclass HTTPBenchmark and to override the
``get_worker`` method to implement your own test logic. In this regard you can
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
    import random

    USER_IDS = [1111, 2222, 3333, 4444]

    _url = lambda x: ''.join(['http://my-host.tld/', x])

    class MyBenchmark(HTTPBenchmark):
        def get_worker(self):
            '''
            get_worker should return a callable that will be called by the async http client
            '''
            if random.choice([True, False]):
                return self.new_user
            return self.returning_user

        def new_user(self):
            user_id = random.choice(USER_IDS)
            self.log.debug("New user: %s" % user_id)

            def handle_register(response, friends):
                # ... handle registration response ...

                if failure:
                    self.log.error("Indicate reason for failure")
                    self.log.debug("Show debugging info if you want")
                    return self.finish_request(False)

                self.next_step(user_id, friends['friendList'][0])

            self.open_json(_url("register?uid=%d" % user_id), handle_register)

        def returning_user(self):
            user_id = random.choice(USER_IDS)
            self.log.debug("Returning user: %s" % user_id)

            def handle_login(response, friends):
                # ... handle login response ...

                if failure:
                    self.log.error("Indicate reason for failure")
                    self.log.debug("Show debugging info if you want")
                    return self.finish_request(False)

                self.next_step(user_id, friends['friendList'][0])

           self.open_json(_url("login?uid=%d" % user_id), handle_login)

        def next_step(self, user_id, friend_id):
            # ... do something else ...
            if failure:
                self.log.error("Indicate reason for failure")
                self.log.debug("Show debugging info if you want")
                return self.finish_request(False)

            # success!
            return self.finish_request(True)

    if __name__ == '__main__':
        MyBenchmark().main()


Essentials
^^^^^^^^^^

* ``get_worker`` should return a callable that will be used by the async HTTP
  client. Whenever the client has a free slot based on the concurrency limits
  it will invoke your worker function.

* ``self.get(url, callback)`` is used to make a GET request, pass a callable
  to the callback argument and it will receive the response object back as an
  argument when the operations completes.

* ``self.post(url, params={}, callback)`` is used to POST data. ``params``
  should be a dictionary and will be sent as the POST data. It functions
  the same as ``get`` otherwise.

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
* Upgrade Tornado
