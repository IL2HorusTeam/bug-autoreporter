# coding: utf-8
"""
Create bug issues on GitHub automatically when an exception occurs.
"""

import itertools
import six
import traceback

from github import GitHub
from Levenshtein.StringMatcher import StringMatcher
from operator import itemgetter

from .constants import (
    DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
    SIMILAR_ISSUES_MIN_RATIO, SIMILAR_ISSUES_MAX_SUGGESTIONS,
)
from .text import force_text


class BugReporter(object):

    def __init__(self, access_token, repo_owner, repo_name):
        gh = GitHub(access_token=access_token)
        self.api = gh.repos(repo_owner)(repo_name)
        self.matcher = StringMatcher()
        self.ensure_labels_exist()

    @property
    def labels_api(self):
        return self.api('labels')

    @property
    def issues_api(self):
        return self.api('issues')

    @property
    def existing_issues(self):
        return self.issues_api.get(state='all')

    def ensure_labels_exist(self):
        """
        Call this to ensure that all needed labels exist.
        """
        labels = itertools.chain(*[
            container.constants()
            for container in (
                DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
            )
        ])
        existing_titles = map(lambda x: x['name'], self.labels_api.get())

        for label in labels:
            if label.title not in existing_titles:
                self.labels_api.post(name=label.title, color=label.color)

    def get_issue(self, title):
        """
        Try to get non-duplicate with same title. Return duplicate or `None`
        otherwise.
        """
        title = title.lower()
        result = None

        for issue in self.existing_issues:
            if title == issue['title'].lower():
                if self.is_duplicate(issue):
                    result = issue
                else:
                    return issue

        return result

    @classmethod
    def is_duplicate(cls, issue):
        return cls.has_label(issue, DuplicateIssueLabels.titles())

    @classmethod
    def is_valid(cls, issue):
        return not cls.has_label(issue, InvalidIssueLabels.titles())

    @staticmethod
    def has_label(issue, labels):
        issue_labels = set([label['name'] for label in issue['labels']])
        searched_labels = set(labels)
        return bool(issue_labels.intersection(searched_labels))

    def reopen_issue(self, issue, comment=None):
        issue_api = self.issues_api(issue['number'])
        issue_api.patch(state='open')
        return comment and self._post_comment(issue_api, comment)

    @classmethod
    def _post_comment(cls, issue_api, comment):
        comment = force_text(comment, "issue comment")
        if comment:
            body_chunks = [comment, ]
            cls._append_traceback(body_chunks)
            comment_body = '\n'.join(body_chunks)
            return issue_api('comments').post(body=comment_body)

    def report_issue(self, title, description=None):
        body = self._get_issue_body(description)
        labels = NewIssueLabels.titles()
        return self.issues_api.post(title=title, body=body, labels=labels)

    @classmethod
    def _get_issue_body(cls, description):
        body_chunks = []

        if description:
            description = force_text(description, "issue description")
            body_chunks.append(description)

        cls._append_traceback(body_chunks)
        return "\n".join(body_chunks)

    @staticmethod
    def _append_traceback(container):
        if container:
            container.append("")

        the_traceback = traceback.format_exc()
        container.extend([
            "Traceback:",
            "```\n{}```".format(the_traceback),
        ])

    def get_similar_issues(self, title):
        title = six.text_type(title).lower()
        results = []

        for issue in self.existing_issues:
            other_title = six.text_type(issue['title']).lower()

            if other_title == title:
                continue

            self.matcher.set_seqs(other_title, title)
            ratio = self.matcher.ratio()

            if ratio >= SIMILAR_ISSUES_MIN_RATIO:
                results.append((issue, ratio))

        key = itemgetter(1)
        results = sorted(results, key=key)[:SIMILAR_ISSUES_MAX_SUGGESTIONS]

        return [issue for issue, ratio in results]

    def shorten_issue(self, issue):
        return {
            'number': issue['number'],
            'url': issue['html_url'],
            'state': issue['state'],
            'is_valid': self.is_valid(issue),
        }
