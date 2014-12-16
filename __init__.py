# -*- coding: utf-8 -*-
"""
Create bug issues on GitHub automatically when an exception occurs.
"""

import itertools

from github import GitHub, ApiNotFoundError
from Levenshtein.StringMatcher import StringMatcher

from .constants import (
    DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
)


class BugAutoreporter(object):

    def __init__(self, access_token, repo_owner, repo_name):
        gh = GitHub(access_token=access_token)
        self.api = gh.repos(repo_owner)(repo_name)
        self._ensure_labels_exist()

        self.matcher = StringMatcher()

    def _ensure_labels_exist(self):
        labels = itertools.chain(*[
            container.constants()
            for container in (
                DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
            )
        ])
        labels_api = self.api('labels')
        for label in labels:
            try:
                labels_api(label.title).get()
            except ApiNotFoundError:
                labels_api.post(name=label.title, color=label.color)
