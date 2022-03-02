import argparse
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
import json
import logging
import os
from pathlib import Path
import re
from typing import List
from urllib.parse import urlparse


import requests
import yaml


@lru_cache(maxsize=1)
def token() -> str:
    return os.environ["CIRCLE_TOKEN"]


# NOTE: on hierarchy
# BuildLink
# └── BuildStep
#     └── BuildAction
#         └── BuildOutput
#             └── logs
@dataclass
class BuildOutput:
    message: str
    logs: List[str] = field(init=False)
    time: str  # ISO8601
    type: str  # e.g. "out"

    def __post_init__(self):
        self.logs = self.message.split("\n")


@dataclass
class BuildAction:
    name: str
    output_url: str  # presigned S3 URL; no authentication required
    bash_command: str
    infrastructure_fail: bool
    status: str

    @cached_property
    def output(self) -> List[BuildOutput]:
        # lazily evaluated, and cached
        # so we dont need to fetch again.
        if req := requests.get(self.output_url):
            outputs = json.loads(req.text)
            return [BuildOutput(**o) for o in outputs]
        return []


@dataclass
class BuildStep:
    name: str
    actions: List[BuildAction]


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

        return cls(hostname=hostname, **matched.groupdict())

    def __post_init__(self):
        # must be for CircleCI Cloud
        assert self.hostname == "app.circleci.com"


def validate(links: List[BuildLink]):
    logging.info("Validate")
    a, b, *_ = links  # only concerned with first 2 links

    assert a.vcs == b.vcs, f"Different VCS found: { a.vcs= }. {b.vcs= }"

    assert (
        a.project == b.project
    ), f"Different projects found: { a.project= }. {b.project= }"


def __extract_steps(data: dict) -> List[BuildStep]:
    def _extract(d: dict) -> dict:
        return {
            "name": d["name"],
            "output_url": d["output_url"],
            "status": d["status"],
            "infrastructure_fail": d["infrastructure_fail"],
            "bash_command": d["bash_command"],
        }

    def _build_step(step: dict) -> BuildStep:
        build_actions = [BuildAction(**_extract(act)) for act in step["actions"]]
        return BuildStep(
            name=step["name"],
            actions=build_actions,
        )

    return [_build_step(step) for step in data["steps"]]


def __output_build_info(_link: BuildLink, steps: List[BuildStep], index: int):
    # generate a dict
    actions = [act for s in steps for act in s.actions]

    def _logs(act: BuildAction) -> dict:
        return {
            "name": act.name,
            "command": act.bash_command,
            "status": act.status,
            "output": [log for o in act.output for log in o.logs],
        }

    dct = {
        "vcs": {
            "project": f"{link.vcs}/{link.project}",
            "branch": "",
            "commit": "",
            "author": "",
        },
        "build": {
            "pipeline_id": link.pipeline_id,
            "workflow_id": link.workflow_id,
            "job_id": link.job_id,
        },
        "steps": [_logs(act) for act in actions],
    }

    # outputs to YAML
    output_dir = "job_info"  # relative to cur dir
    Path(output_dir).mkdir(exist_ok=True) # create if not exists
    output_path = os.path.join(output_dir, f"{index}.yml")

    with open(output_path, "w") as f:
        yaml.dump(dct, f)
        logging.info(f"-> Written to {output_path}")


def info(link: BuildLink, index: int):
    logging.info("Info")

    url = (
        f"https://circleci.com/api/v1.1/project/{link.vcs}/{link.project}/{link.job_id}"
    )
    response = requests.get(url, headers={"Circle-Token": token()})
    data = response.json()
    steps = __extract_steps(data)

    __output_build_info(link, steps, index)


def setup_logging():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description="Compare 2 CircleCI Cloud builds")
    parser.add_argument(
        "build_links",
        metavar="URL",
        nargs=2,
        type=str,
        help="Job build link URL",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run sanity checks on URLs",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Extract build information from URL",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="index of build link (URL)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()

    links = [BuildLink.from_url(url) for url in args.build_links]

    if args.validate:
        validate(links)

    if args.info and args.index >= 0:
        link = links[args.index]
        info(link, args.index)
