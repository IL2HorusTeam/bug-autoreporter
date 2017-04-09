# coding: utf-8


def force_text(text, name):
    if callable(text):
        try:
            text = text()
        except Exception as e:
            text = (
                "`{}` occured while getting {}: {}"
                .format(e.__class__.__name__, name, str(e))
            )

    if text:
        return str(text)
