HTTPBenchmark
=============

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
