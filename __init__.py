# -*- coding: utf-8 -*-
"""
Create bug issues on GitHub automatically when an exception occurs.
"""

import itertools
import six

from github import GitHub
from Levenshtein.StringMatcher import StringMatcher
from operator import itemgetter

from .constants import (
    DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
    SIMILAR_ISSUES_MIN_RATIO, SIMILAR_ISSUES_MAX_SUGGESTIONS,
)


class BugAutoreporter(object):

    def __init__(self, access_token, repo_owner, repo_name):
        gh = GitHub(access_token=access_token)
        self.api = gh.repos(repo_owner)(repo_name)
        self._ensure_labels_exist()

        self.matcher = StringMatcher()

    @property
    def labels_api(self):
        return self.api('labels')

    @property
    def issues_api(self):
        return self.api('issues')

    @property
    def existing_issues(self):
        return self.issues_api.get(state='all')

    def _ensure_labels_exist(self):
        known_labels = itertools.chain(*[
            container.constants()
            for container in (
                DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
            )
        ])
        existing_titles = map(lambda x: x['name'], self.labels_api.get())

        for label in known_labels:
            if label.title not in existing_titles:
                self.labels_api.post(name=label.title, color=label.color)

    def get_issue(self, title):
        for issue in self.existing_issues:
            if title.lower() == issue['title'].lower():
                return issue

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
