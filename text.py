# -*- coding: utf-8 -*-

import six


def force_text(text, name):
    if callable(text):
        try:
            text = text()
        except Exception as e:
            text = ("`{}` occured while getting {}: {}"
                    .format(e.__class__.__name__,
                            name,
                            six.text_type(e)))
    if text:
        return six.text_type(text)
