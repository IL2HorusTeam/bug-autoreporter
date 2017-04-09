# -*- coding: utf-8 -*-

import os

from setuptools import setup


__here__ = os.path.abspath(os.path.dirname(__file__))


def split_requirements(lines):
    requirements, dependencies = [], []

    for line in lines:
        if line.startswith('-e'):
            line = line.split(' ', 1)[1]
            dependencies.append(line)
            line = line.split('#egg=', 1)[1]

        requirements.append(line)

    return requirements, dependencies


with open(os.path.join(__here__, 'requirements.txt')) as f:
    REQUIREMENTS = [x.strip() for x in f]
    REQUIREMENTS = [x for x in REQUIREMENTS if x and not x.startswith('#')]
    REQUIREMENTS, DEPENDENCIES = split_requirements(REQUIREMENTS)

README = open(os.path.join(__here__, 'README.rst')).read()


setup(
    name='il2fb-github-bug-reporter',
    version='1.0.0',
    description="GitHub bug reporter for IL-2 FB libraries",
    long_description=README,
    keywords=[
        'il2', 'il-2', 'fb', 'bug', 'issue', 'github', 'asyncio',
    ],
    license='LGPLv3',
    url='https://github.com/IL2HorusTeam/il2fb-github-bug-reporter',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    namespace_packages=[
        'il2fb',
        'il2fb.github',
    ],
    packages=[
        'il2fb.github.bug_reporter',
    ],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    dependency_links=DEPENDENCIES,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
    ],
    platforms=[
        'any',
    ],
)
