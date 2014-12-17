# -*- coding: utf-8 -*-


def format_issue_link(issue):
    return format_html_link(url=issue['html_url'],
                            text="issue #{}".format(issue['number']))


def format_html_link(url, text):
    return "<a href='{}' target='_blank'>{}</a>".format(url, text)
