# -*- coding: utf-8 -*-
"""Plugin configuration module for pytest-ngsfixtures"""
import itertools
from collections import namedtuple
from pytest_ngsfixtures import factories

Config = namedtuple('Config', 'SIZES SAMPLES POPULATIONS SAMPLE_LAYOUTS')

conf = Config(SIZES = ["tiny", "small", "medium", "yuge"],
              SAMPLES = ['CHS.HG00512', 'CHS.HG00513',
                         'PUR.HG00731', 'PUR.HG00733',
                         'PUR.HG00731.A', 'PUR.HG00731.B',
                         'PUR.HG00733.A', 'PUR.HG00733.B',
                         'YRI.NA19238', 'YRI.NA19239'],
              POPULATIONS = ["CHS", "PUR", "YRI"],
              SAMPLE_LAYOUTS= ["sample", "sample_run", "project_sample_run",
                               "pop_sample", "pop_sample_run", "pop_project_sample_run"]
)

_help_ngs_size = "select sample size (choices: {})".format(", ".join("'{}'".format(x) for x in conf.SIZES))
_help_ngs_layout="select predefined sample layout(s) (allowed choices: {})".format(", ".join("'{}'".format(x) for x in conf.SAMPLE_LAYOUTS))
_help_ngs_show_fixture="show fixture layout"

def pytest_addoption(parser):
    group = parser.getgroup("ngsfixtures", "next-generation sequencing fixture options")
    group.addoption(
        '-X',
        '--ngs-size',
        action='store',
        dest='ngs_size',
        default='tiny',
        help=_help_ngs_size,
        choices=conf.SIZES,
        metavar="size",
    )
    group.addoption(
        '-L',
        '--ngs-layout',
        action='store',
        dest='ngs_layout',
        default=['sample'],
        help=_help_ngs_layout,
        nargs="+",
        metavar="layout",
        choices=conf.SAMPLE_LAYOUTS,
    )
    group.addoption(
        '-F',
        '--ngs-show-fixture',
        action="store_true",
        dest="ngs_show_fixture",
        default=False,
        help=_help_ngs_show_fixture,
    )


flat = factories.sample_layout(samples=['CHS.HG00512'])

kwargs =  {'samples' : ['PUR.HG00731.A', 'PUR.HG00731.B', 'PUR.HG00733.A'],
           'platform_units' : ['010101_AAABBB11XX', '020202_AAABBB22XX', '010101_AAABBB11XX'],
           'paired_end' : [True] * 3,
}


sample = factories.sample_layout(
    dirname="sample",
    runfmt="{SM}/{SM}_{PU}",
    **kwargs,
)

sample_run = factories.sample_layout(
    dirname="sample_run",
    runfmt="{SM}/{PU}/{SM}_{PU}",
    **kwargs,
)

sample_project_run = factories.sample_layout(
    dirname="sample_project_run",
    runfmt="{SM}/{BATCH}/{PU}/{BATCH}_{PU}",
    batches=["p1", "p2", "p1"],
    **kwargs,
)


kwargs =  {'samples' :  ['PUR.HG00731.A', 'PUR.HG00731.B', 'PUR.HG00733.A'] + ['CHS.HG00512', 'CHS.HG00513'] + ['YRI.NA19238', 'YRI.NA19239'],
           'platform_units' : ['010101_AAABBB11XX', '020202_AAABBB22XX', '010101_AAABBB11XX'] + ['010101_AAABBB11XX', '020202_AAABBB22XX'] * 2,
           'populations' : ['PUR'] * 3 + ['CHS'] * 2 + ['YRI'] * 2,
           'paired_end' : [True] * 7,
           'use_short_sample_names' : False,
}

pop_sample = factories.sample_layout(
    dirname="pop_sample",
    runfmt="{POP}/{SM}/{SM}_{PU}",
    **kwargs,
)

pop_sample_run = factories.sample_layout(
    dirname="pop_sample_run",
    runfmt="{POP}/{SM}/{PU}/{SM}_{PU}",
    **kwargs,
)

pop_sample_project_run = factories.sample_layout(
    dirname="pop_project_sample_run",
    runfmt="{POP}/{SM}/{BATCH}/{PU}/{SM}_{PU}",
    batches=["p1", "p2", "p1"] + ["p1", "p2"] * 2,
    **kwargs,
)

ref = factories.reference_layout(dirname="ref")
scaffolds= factories.reference_layout(label="scaffolds", dirname="scaffolds")

