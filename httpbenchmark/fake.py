"""
A bunch of helper functions that generate fake data for interacting with
web services
"""

import random

def graph_id():
    return random.randrange(100000000, 999999999)

def name():
    starts = ["Ae", "Di", "Mo", "Fam"]
    ends = ["dar", "kil", "glar", "tres"]

    return "".join([random.choice(starts), random.choice(ends)])

def address():
    addr_1 = " ".join([
        str(random.randrange(100, 9999)),
        random.choice(["Fake", "Phony", "Bogus"]),
        random.choice(["St", "Ave", "Rd"]),
    ])

    if random.choice([True, False, False, True, True, False]):
        addr_2 = ''
    else:
        addr_2 = " ".join([
            random.choice(["Apt", "Suite", "Unit"]),
            str(random.randrange(1, 999))
        ])

    cities = ["Toronto", "Halifax", "Calgary", "Vancouver"]
    provs =  ["ON"     , "NS"     , "AB"     , "BC"]
    postal = ["M5A1A1" , "B3J2T2" , "T2E7P5" , "V6C3N3"]
    phone =  ["416"    , "902"    , "403"    , "604"]
    
    city_num = random.randrange(0, 4)

    return {
        'address_1': addr_1,
        'address_2': addr_2,
        'city': cities[city_num],
        'province': provs[city_num],
        'postal_code': postal[city_num],
        'phone': '1%s5551212' % phone[city_num],
    }
