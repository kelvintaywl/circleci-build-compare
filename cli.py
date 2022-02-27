import argparse
from dataclasses import dataclass
import logging
import os
import re
from typing import List
from urllib.parse import urlparse


@dataclass
class BuildLink:
    PATH_EXPRESSION = re.compile(
        "^/pipelines/(?P<vcs>github|bitbucket)/(?P<project>.+/.+)/(?P<pipeline_id>\d+)/workflows/(?P<workflow_id>[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/jobs/(?P<job_id>\d+)"
    )

    hostname: str
    vcs: str
    project: str
    pipeline_id: int
    workflow_id: str
    job_id: int

    @classmethod
    def from_url(cls, url: str):
        info = urlparse(url)
        hostname, path = info.hostname, info.path
        matched = cls.PATH_EXPRESSION.search(path)
        assert matched, f"Failed to parse info from URL: {url}"

        return cls(
            hostname=hostname,
            **matched.groupdict()
        )

    def __post_init__(self):
        # must be for CircleCI Cloud
        assert self.hostname == "app.circleci.com"


def validate(links: List[BuildLink]):
    logging.info("Validate")
    a, b, *_ = links  # only concerned with first 2 links

    assert a.vcs == b.vcs, f"Different VCS found: { a.vcs= }. {b.vcs= }"
    
    assert a.project == b.project, f"Different projects found: { a.project= }. {b.project= }"


def info(link: BuildLink):
    logging.info(link)


def setup_logging():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Compare 2 CircleCI Cloud builds')
    parser.add_argument(
        'build_links',
        metavar='URL', nargs=2,
        type=str,
        help='Job build link URL',
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run sanity checks on URLs',
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Extract build information from URL',
    )
    parser.add_argument(
        '--index',
        type=int,
        help='index of build link (URL)',
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()

    links = [
        BuildLink.from_url(url)
        for url in args.build_links
    ]

    if args.validate:
        validate(links)

    if args.info and args.index:
        link = links[args.index]
        info(link)
