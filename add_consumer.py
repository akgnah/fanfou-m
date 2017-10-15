#!/usr/bin/python
# -*- coding: utf-8 -*-
import uuid

import models

consumers = [
    {'key': 'consumer key', 'secret': 'consumer secret'},
    {'key': 'consumer key', 'secret': 'consumer secret'},
    {'key': 'consumer key', 'secret': 'consumer secret'},
]


def gen_uuid(d):
    s = ''.join([str(v) for v in d.values()])
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))


if __name__ == '__main__':
    for i, consumer in enumerate(consumers):
        models.consumer.set(gen_uuid(consumer), 'consumer_%s' % i, consumer, 'public')
