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
from .text import force_text, html_link, html_list, issue_link


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

    def report_issue(self, title, description=None, reopen_comment=None):
        issue = self.get_issue(title)
        if issue:
            result = self._on_issue_exists(issue, reopen_comment)
        else:
            result = self._report_new_issue(title, description)

        similar_issues = self.propose_similar_issues(title)
        if similar_issues:
            result = result + "<br>" + similar_issues

        return result

    def get_issue(self, title):
        """
        Try to get non-dublicate with same title. Return dublicate or `None`
        otherwise.
        """
        title = title.lower()
        result = None

        for issue in self.existing_issues:
            if title == issue['title'].lower():
                if self.is_dublicate(issue):
                    result = issue
                else:
                    return issue

        return result

    @classmethod
    def is_dublicate(cls, issue):
        return cls.has_label(issue, DuplicateIssueLabels.titles())

    def _on_issue_exists(self, issue, reopen_comment):
        if issue['state'] == 'open':
            return self._on_issue_is_already_open(issue)
        else:
            if self.can_be_reopened(issue):
                return self._reopen_issue(issue, reopen_comment)
            else:
                return self._on_issue_cannot_be_reopened(issue)

    @staticmethod
    def _on_issue_is_already_open(issue):
        return ("This case was already reported in the {}."
                .format(issue_link(issue)))

    @classmethod
    def can_be_reopened(cls, issue):
        return not cls.has_label(issue, InvalidIssueLabels.titles())

    @staticmethod
    def has_label(issue, labels):
        issue_labels = set([label['name'] for label in issue['labels']])
        searched_labels = set(labels)
        return bool(issue_labels.intersection(searched_labels))

    def _reopen_issue(self, issue, reopen_comment):
        issue_api = self.issues_api(issue['number'])
        issue_api.patch(state='open')

        ending = "It was reopened"

        if reopen_comment:
            comment = self._post_comment(issue_api, reopen_comment)
            if comment:
                ending = html_link(url=comment['html_url'], text=ending)

        return ("Seems like this case was fixed in the {} earlier. {}."
                .format(issue_link(issue), ending))

    @classmethod
    def _post_comment(cls, issue_api, comment):
        comment = force_text(comment, "issue comment")
        if comment:
            body_chunks = [comment, ]
            cls._append_traceback(body_chunks)
            comment_body = '\n'.join(body_chunks)
            return issue_api('comments').post(body=comment_body)

    def _on_issue_cannot_be_reopened(self, issue):
        return ("This is a known case which was reported in the {}. However, "
                "it's not going to be fixed."
                .format(issue_link(issue)))

    def _report_new_issue(self, title, description):
        body = self._get_issue_body(description)
        labels = NewIssueLabels.titles()
        issue = self.issues_api.post(title=title, body=body, labels=labels)
        return ("This case was reported in a new {}."
                .format(issue_link(issue)))

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

    def propose_similar_issues(self, title):
        issues = self.get_similar_issues(title)
        if issues:
            links = map(lambda i: issue_link(i, show_title=True), issues)
            return "<span>Similar issues</span>:<br>" + html_list(links)

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
