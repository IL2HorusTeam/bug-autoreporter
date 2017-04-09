# coding: utf-8

import asyncio
import itertools
import signal
import sys
import traceback

from operator import itemgetter

import aiohttp
import ujson as json

from fuzzywuzzy import fuzz
from yarl import URL

from .constants import DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels
from .text import force_text


ROOT_URL = URL("https://api.github.com")


class BugReporter:

    def __init__(self, loop, access_token, repo_owner, repo_name):
        self.loop = loop
        self.api_base_url = ROOT_URL / "repos" / repo_owner / repo_name
        self.http_headers = {
            'Authorization': "token {}".format(access_token),
        }
        self.client = aiohttp.ClientSession(loop=self.loop)

    def clean_up(self):
        self.client.close()

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

    async def ensure_labels_exist(self):
        """
        Call to ensure that all needed labels exist.
        """
        labels = itertools.chain(*[
            container.constants()
            for container in (
                DuplicateIssueLabels, InvalidIssueLabels, NewIssueLabels,
            )
        ])

        existing_labels = await self._get_existing_labels()
        existing_titles = [x['name'] for x in existing_labels]

        for label in labels:
            if label.title not in existing_titles:
                await self._create_label(label.title, label.color)

    async def _get_existing_labels(self):
        async with self.client.get(
            self.api_base_url / "labels",
            headers=self.http_headers,
        ) as response:
            text = await response.text()

        return json.loads(text)

    async def _create_label(self, name, color):
        data = json.dumps({'name': name, 'color': color}).encode()
        await self.client.post(
            self.api_base_url / "labels",
            headers=self.http_headers,
            data=data,
        )

    async def get_issue(self, title):
        """
        Try to get non-duplicate with same title.

        Return duplicate or `None` otherwise.

        """
        title = title.lower()
        result = None

        issues = await self.get_existing_issues()
        for issue in issues:
            if title == issue['title'].lower():
                if self.is_duplicate(issue):
                    result = issue
                else:
                    return issue

        return result

    async def get_similar_issues(self, title, min_ratio=60, max_suggestions=5):
        title = str(title).lower()
        results = []

        issues = await self.get_existing_issues()
        for issue in issues:
            other_title = str(issue['title']).lower()
            issue

            if other_title == title:
                continue

            ratio = fuzz.partial_ratio(other_title, title)
            if ratio >= min_ratio:
                results.append((issue, ratio))

        key = itemgetter(1)
        results = sorted(results, key=key)[:max_suggestions]

        return list(map(itemgetter(0), results))

    async def get_existing_issues(self):
        async with self.client.get(
            self.api_base_url / "issues",
            headers=self.http_headers,
            params={
                'state': "all",
                'filter': "all",
            },
        ) as response:
            text = await response.text()

        return json.loads(text)

    def shorten_issue(self, issue):
        return {
            'number': issue['number'],
            'url': issue['html_url'],
            'state': issue['state'],
            'is_valid': self.is_valid(issue),
        }

    async def report_issue(self, title, description=None):
        body = self._get_issue_body(description)
        labels = NewIssueLabels.titles()
        data = json.dumps({
            'title': title, 'body': body, 'labels': labels,
        }).encode()

        async with self.client.post(
            self.api_base_url / "issues",
            headers=self.http_headers,
            data=data,
        ) as response:
            text = await response.text()

        return json.loads(text)

    @classmethod
    def _get_issue_body(cls, description=None):
        body_chunks = []

        if description:
            description = force_text(description, "issue description")
            body_chunks.append(description)

        tb = cls._get_traceback()
        if tb:
            body_chunks.extend(tb)

        return "\n".join(body_chunks)

    async def reopen_issue(self, issue, comment=None):
        data = json.dumps({'state': 'open'}).encode()
        await self.client.patch(
            self.api_base_url / "issues" / str(issue['number']),
            headers=self.http_headers,
            data=data,
        )
        if comment:
            await self._post_comment(issue, comment)

    async def _post_comment(self, issue, comment):
        comment = force_text(comment, "issue comment")

        if not comment:
            return

        body_chunks = [comment, ]

        tb = self._get_traceback()
        if tb:
            body_chunks.extend(tb)

        data = json.dumps({"body": '\n'.join(body_chunks)}).encode()

        await self.client.post(
            self.api_base_url / "issues" / str(issue['number']) / "comments",
            headers=self.http_headers,
            data=data,
        )

    @staticmethod
    def _get_traceback():
        etype, value, tb = sys.exc_info()
        if tb:
            formatted = ''.join(traceback.format_exception(etype, value, tb))
            return [
                ""
                "Traceback:",
                "```\n{}```".format(formatted),
            ]
