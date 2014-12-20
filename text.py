# -*- coding: utf-8 -*-

import six


def issue_link(issue, show_title=False):
    text = "issue #{}".format(issue['number'])

    if show_title:
        text += ": \"{}\"".format(issue['title'])

    return html_link(url=issue['html_url'], text=text)


def html_link(url, text):
    return "<a href='{}' target='_blank'>{}</a>".format(url, text)


def html_list(items):
    elements = [
        "<ol>",
    ]
    elements.extend([
        "<li>{}</li>".format(item) for item in items
    ])
    elements.append("</ol>")
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
