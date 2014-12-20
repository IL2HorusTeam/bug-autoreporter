# -*- coding: utf-8 -*-

import six


def issue_number_link(issue):
    return html_link(url=issue['html_url'],
                     text="issue #{}".format(issue['number']))


def issue_link(issue):
    return html_link(url=issue['html_url'],
                     text=issue['title'])


def html_link(url, text):
    return "<a href='{}' target='_blank'>{}</a>".format(url, text)


def html_list(items):
    elements = [
        "<ul>",
    ]
    elements.extend([
        "<li>{}</li>".format(item) for item in items
    ])
    elements.append("</ul>")
    return ''.join(elements)


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
