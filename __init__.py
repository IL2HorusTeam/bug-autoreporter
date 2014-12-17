# -*- coding: utf-8 -*-
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
from .format import format_issue_link


class BugAutoreporter(object):

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

    def report_issue(self, title, description=None):
        issue = self.get_issue(title)
        if issue:
            return self._on_issue_exists(issue)
        else:
            return self._report_new_issue(title, description)

    def _on_issue_exists(self, issue):
        pass

    def _report_new_issue(self, title, description):
        body = self._get_body(description)
        labels = NewIssueLabels.titles()
        issue = self.issues_api.post(title=title, body=body, labels=labels)
        return ("This case was reported in new {}."
                .format(format_issue_link(issue)))

    @classmethod
    def _get_body(cls, description):
        body_chunks = []
        if description:
            body_chunks.extend(cls._get_description(description))
        body_chunks.extend(cls._get_traceback())
        return "\n".join(body_chunks)

    @staticmethod
    def _get_description(description):
        if callable(description):
            try:
                description = description()
            except Exception as e:
                description = ("{} occured while getting issue description: {}"
                               .format(e.__class__.__name__, six.text_type(e)))

        return [
            six.text_type(description),
            "",
        ]

    @staticmethod
    def _get_traceback():
        the_traceback = traceback.format_exc()
        return [
            "Traceback:",
            "```\n{}```".format(the_traceback),
        ]

    def get_issue(self, title):
        for issue in self.existing_issues:
            if title.lower() == issue['title'].lower():
                return issue

    @classmethod
    def is_dublicate(cls, issue):
        return cls.has_label(issue, DuplicateIssueLabels.titles())

    @classmethod
    def can_be_reopened(cls, issue):
        return not cls.has_label(issue, InvalidIssueLabels.titles())

    @staticmethod
    def has_label(issue, labels):
        issue_labels = set([label['name'] for label in issue['labels']])
        searched_labels = set(labels)
        return bool(issue_labels.intersection(searched_labels))

    def propose_similar_issues(self, title):
        title = six.text_type(title)

        results = []

        for issue in self.existing_issues:
            other_title = six.text_type(issue['title'])
            self.matcher.set_seqs(title.lower(), other_title.lower())
            ratio = self.matcher.ratio()

            if ratio >= SIMILAR_ISSUES_MIN_RATIO:
                results.append((other_title, ratio))

        key = itemgetter(1)
        results = sorted(results, key=key)[:SIMILAR_ISSUES_MAX_SUGGESTIONS]

        return [title for title, ratio in results]
