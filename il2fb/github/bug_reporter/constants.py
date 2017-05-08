# coding: utf-8

from candv import SimpleConstant, Constants, with_constant_class


class Label(SimpleConstant):

    def __init__(self, title, hex_color):
        super(Label, self).__init__()
        self.title = title
        self.color = hex_color


class Labels(with_constant_class(Label), Constants):

    @classmethod
    def titles(cls):
        return [c.title for c in cls.constants()]


class DuplicateIssueLabels(Labels):
    DUPLICATE = Label('duplicate', 'cccccc')


class InvalidIssueLabels(Labels):
    INVALID = Label('invalid', 'e6e6e6')
    WONTFIX = Label('wontfix', 'ffffff')


class NewIssueLabels(Labels):
    BUG = Label('bug', 'e11d21')
    AUTO_REPORT = Label('auto-report', 'fbca04')
