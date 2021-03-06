# -*- coding: utf-8 -*-
import os
import re
import py
import logging
import itertools
import pytest
from pytest_ngsfixtures.config import sample_conf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOTDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATADIR = os.path.realpath(os.path.join(ROOTDIR, "pytest_ngsfixtures", "data"))
REPO = "https://raw.githubusercontent.com/percyfal/pytest-ngsfixtures/master"
DOWNLOAD_SIZES = ["yuge"]


class ParameterException(Exception):
    pass


class SampleException(Exception):
    pass

ref_dict = {}

for f in os.listdir(os.path.join(DATADIR, "ref")):
    if f in ("Makefile", "Snakefile.test"):
        continue
    ref_dict[f] = os.path.join(DATADIR, "ref", f)

ref_always = ['ERCC_spikes.gb', 'pAcGFP1-N1.fasta']


def check_samples(samples):
    """Check the sample names are ok"""
    if not all(x in sample_conf.SAMPLES for x in samples):
        raise SampleException("invalid sample name: choose from {}".format(sample_conf.SAMPLES))


def get_config(request):
    """Return a dictionary with config options."""
    config = {}
    options = [
        'size',
    ]
    for option in options:
        option_name = 'ngs_' + option
        conf = request.config.getoption(option_name) or \
            request.config.getini(option_name)
        config[option] = conf
    return config


def download_sample_file(fn, size, dry_run=False, force=False):
    """Download sample file if it doesn't yet exist

    Setup urllib connection and download data file.

    Params:
      fn (str): file name as it appears in installed pytest_ngsfixtures data repository
      size (str): fixture file size
      dry_run (bool): don't do anything if set
      force (bool): force download

    Returns:
      url (str): url of target file if dry_run option passed, None otherwise

    """
    if size not in DOWNLOAD_SIZES:
        return
    if os.path.exists(fn) and not force:
        return
    else:
        import urllib.request
        import shutil
        url = os.path.join(REPO,
                           os.path.relpath(os.path.realpath(fn),
                                           os.path.realpath(ROOTDIR)))
        if os.path.exists(fn):
            logger.info("File '{}' exists but force option passed; downloading file from git repo to local pytest_ngsfixtures installation location '{}'".format(fn, url))
        else:
            logger.info("File '{}' doesn't exist; downloading it from git repo to local pytest_ngsfixtures installation location '{}'".format(fn, url))
        if dry_run:
            return url
        try:
            if not os.path.exists(os.path.dirname(fn)):
                os.makedirs(os.path.dirname(fn))
            with urllib.request.urlopen(url) as response, open(fn, 'wb') as fh:
                shutil.copyfileobj(response, fh)
        except Exception as e:
            logger.error("Downloading '{}' failed: {}".format(url, e))
            raise


def _check_file_exists(fn, size):
    if size not in DOWNLOAD_SIZES:
        return
    if os.path.exists(fn):
        return
    else:
        logger.info("Sequence data in {} is not bundled with conda/PyPI packages to save space".format(size))
        logger.info("")
        logger.info("   Launch script 'pytest_ngsfixtures_download_data.py' to download missing files")
        logger.info("")
        raise FileNotFoundError


def safe_symlink(p, src, dst):
    """Safely make symlink.

    Make symlink from src to dst in LocalPath p. If src, dst are
    strings, they will be joined to p, assuming they are relative to
    p. If src, dst are LocalPath instances, they are left alone since
    LocalPath objects are always absolute paths.

    Params:
      p (LocalPath): path in which link is setup
      src (str, LocalPath): source file that link points to. If string, assume relative to pytest_ngsfixtures data directory
      dst (str, LocalPath): link destination name. If string, assume relative to path and concatenate; else leave alone

    Returns:
      dst (LocalPath): link name
    """
    if isinstance(src, str):
        if not os.path.isabs(src):
            src = os.path.join(DATADIR, src)
        src = py.path.local(src)
    if dst is None:
        dst = src.basename
    if isinstance(dst, str):
        dst = p.join(dst)
    if not dst.check(link=1):
        dst.dirpath().ensure(dir=True)
        dst.mksymlinkto(src)
    else:
        logger.warn("link {dst} -> {src} already exists! skipping...".format(src=src, dst=dst))
    return dst


def safe_mktemp(tmpdir_factory, dirname=None, **kwargs):
    """Safely make directory"""
    if dirname is None:
        return tmpdir_factory.getbasetemp()
    else:
        p = tmpdir_factory.getbasetemp().join(os.path.dirname(dirname)).ensure(dir=True)
        if kwargs.get("numbered", False):
            p = tmpdir_factory.mktemp(dirname)
        else:
            p = tmpdir_factory.getbasetemp().join(dirname)
            if not p.check(dir=1):
                p = tmpdir_factory.mktemp(dirname, numbered=False)
        return p


def sample_layout(
        runfmt="{SM}",
        sample_prefix="s",
        use_short_sample_names=True,
        read1_suffix="_1.fastq.gz",
        read2_suffix="_2.fastq.gz",
        dirname=None,
        sampleinfo=True,
        combinator=itertools.zip_longest,
        sample_aliases=[],
        samples=[None],
        platform_units=[None],
        batches=[None],
        populations=[None],
        paired_end=[True],
        **kwargs
):
    """Fixture factory for pytest-ngsfixtures sample layouts.

    Generates a directory structure by linking to data files in
    pytest-ngsfixtures data directory. A certain amount of generality
    is allowed in that platform units and batches can be named at
    will. Short sample names can also be used.

    Briefly, sample file names are generated by combining labels in
    the lists **samples** (SM), **platform_units** (PU), **batches**
    (BATCH), and **populations** (POP), and formatting the directory
    structure following the *runfmt* format specification. For
    instance, with samples = ["CHR.HG00512"], populations=None,
    batches=None, platform_units=["010101_AAABBB11XX"], and
    runfmt="{SM}/{PU}/{SM}_{PU}", input files will be organized as
    "CHR.HG00512/010101_AAABBB11XX/CHR.HG00512_010101_AAABBB11XX_1.fastq.gz"
    and similarly for the second read.

    Usage:

    .. code-block:: python

       from pytest_ngsfixtures import factories
       my_layout = factories.sample_layout(
           dirname="foo",
           samples=["CHR.HG00512"],
           platform_units=["010101_AAABBB11XX"],
           populations=["CHR"],
           batches=["batch1"],
           runfmt="{POP}/{SM}/{BATCH}/{PU}/{SM}_{PU}",
       )


    Params:
      runfmt (str): run format string
      sample_prefix (str): sample prefix for short names
      use_short_sample_names (bool): use short sample names
      read1_suffix (str): read1 suffix
      read2_suffix (str): read2 suffix
      dirname (str): data directory name
      sampleinfo (bool): create sampleinfo file
      combinator (fun): function to combine sample, platform unit, batch, population labels
      sample_aliases (list): list of sample alias names
      samples (list): list of sample names
      platform_units (list): list of platform units
      batches (list): list of batch (project) names
      populations (list): list of population names
      paired_end (list): list of booleans indicating if a sample run is paired end (True) or single end (False)

    Returns:
      p (py.path.local): tmp directory with sample layout setup

    """
    if len(sample_aliases) > 0:
        assert len(sample_aliases) == len(samples), "length of sample_aliases ({}) and samples ({}) must be equal".format(len(sample_aliases), len(samples))

    @pytest.fixture(autouse=False)
    def sample_layout_fixture(request, tmpdir_factory):
        """Sample layout fixture. Setup sequence input files according to a
        specified sample organization"""
        check_samples(samples)
        config = get_config(request)
        _samples = samples
        _pop = populations
        _batches = batches
        _pu = platform_units
        _pe = paired_end
        _keys = ['POP', 'PU', 'SM', 'BATCH', 'PE']
        _param_names = ['populations', 'platform_units', 'samples', 'batches', 'paired_end']
        _keys_to_param_names = dict(zip(_keys, _param_names))
        _param_dict = dict(zip(_keys, (_pop, _pu, _samples, _batches, _pe)))
        _layout = [dict(zip(_keys, p)) for p in combinator(_pop, _pu, _samples, _batches, _pe)]
        _sample_counter = 1
        _sample_map = {}
        p = safe_mktemp(tmpdir_factory, dirname, **kwargs)
        i = 0
        for l in _layout:
            srckeys = l.copy()
            if not l["SM"] in _sample_map.keys():
                _sample_map[l["SM"]] = "{}{}".format(sample_prefix, _sample_counter)
                _sample_counter = _sample_counter + 1
            if use_short_sample_names:
                l['SM'] = _sample_map[l['SM']]
            if len(sample_aliases) > 0:
                l['SM'] = sample_aliases[i]
                i += 1
            src = os.path.join(DATADIR, config['size'], srckeys['SM'] + "_1.fastq.gz")
            _check_file_exists(src, config['size'])
            safe_symlink(p, os.path.join(DATADIR, config['size'], srckeys['SM'] + "_1.fastq.gz"),
                         runfmt.format(**l) + read1_suffix)
            if l['PE']:
                safe_symlink(p, os.path.join(DATADIR, config['size'], srckeys['SM'] + "_2.fastq.gz"),
                             runfmt.format(**l) + read2_suffix)

        if sampleinfo:
            outkeys = set([x for x in re.split("[{}/_]", runfmt) if x != ""] + ["fastq"])
            if any(len(x[0]) != len(x[1]) for x in itertools.combinations((_param_dict[y] for y in outkeys if not y == "fastq"), 2)):
                raise ParameterException("all parameters {} must be of equal length for sampleinfo file".format(",".join(_keys_to_param_names[y] for y in outkeys if not y == "fastq")))
            outkeys = sorted(outkeys)
            info = [",".join(outkeys)]
            for l in _layout:
                logger.debug("updating layout: {}".format(l))
                l['fastq'] = runfmt.format(**l) + read1_suffix
                info.append(",".join([l[k] for k in outkeys]))
                if l['PE']:
                    l['fastq'] = runfmt.format(**l) + read2_suffix
                    info.append(",".join([l[k] for k in outkeys]))
            p.join("sampleinfo.csv").write("\n".join(info) + "\n")
        # Alternatively print as debug
        if request.config.option.ngs_show_fixture:
            logger.info("sample_layout")
            logger.info("-------------")
            for x in sorted(p.visit()):
                logger.info(str(x))
        return p
    return sample_layout_fixture


def reference_layout(label="ref", dirname="ref", **kwargs):
    """
    Fixture factory for reference layouts.

    Params:
      label (str): ref or scaffolds layout
      dirname (str): reference directory name


    """
    @pytest.fixture(scope=kwargs.get("scope", "session"), autouse=kwargs.get("autouse", False))
    def reference_layout_fixture(request, tmpdir_factory):
        """Reference layout fixture. Setup the one-chromosome reference files
        or scaffold reference files in a separate directory"""
        p = safe_mktemp(tmpdir_factory, dirname, **kwargs)
        for dst, src in ref_dict.items():
            if dst in ref_always:
                safe_symlink(p, src, dst)
            if label not in dst:
                continue
            if dst.endswith("chrom.sizes"):
                dst = "chrom.sizes"
            safe_symlink(p, src, dst)
        if request.config.option.ngs_show_fixture:
            logger.info("'{}' reference layout".format(label))
            logger.info("------------------------------------")
            for x in sorted(p.visit()):
                logger.info(str(x))
        return p
    return reference_layout_fixture


def filetype(src, dst=None, fdir=None, rename=False, outprefix="test", inprefix=['PUR.HG00731', 'PUR.HG00733'], **kwargs):
    """Fixture factory for file types. This factory is atomic in that it
    generates one fixture for one file.

    Params:
      src (str): fixture file name source
      dst (str): fixture file name destination; link name
      fdir (str): fixture output directory
      rename (bool): rename fixture links
      outprefix (str): output prefix
      inprefix (list): list of input prefixes to substitute
      kwargs (dict): keyword arguments

    """
    dst = os.path.basename(src) if dst is None else dst
    if rename:
        pat = "(" + "|".join(inprefix) + ")"
        dst = re.sub(pat, outprefix, dst)

    @pytest.fixture(scope=kwargs.get("scope", "function"), autouse=kwargs.get("autouse", False))
    def filetype_fixture(request, tmpdir_factory):
        """Filetype fixture"""
        p = safe_mktemp(tmpdir_factory, fdir, **kwargs)
        p = safe_symlink(p, src, dst)
        if request.config.option.ngs_show_fixture:
            logger.info("filetype fixture content")
            logger.info("------------------------")
            logger.info(str(p))
        return p
    return filetype_fixture


def fileset(src, dst=None, fdir=None, **kwargs):
    """
    Fixture factory to generate filesets.

    Params:
      src (list): list of sources
      dst (list): list of destination; if None, use src basename
      fdir (:obj:`str` or :obj:`py._path.local.LocalPath`): output directory

    Returns:
      func: a fixture function
    """
    assert isinstance(src, list), "not a list"
    assert dst is None or isinstance(dst, list), "not a list"
    if dst is None:
        dst = [None]

    @pytest.fixture(scope=kwargs.get("scope", "function"), autouse=kwargs.get("autouse", False))
    def fileset_fixture(request, tmpdir_factory):
        """Fileset factory

        Setup a set of files

        Params:
          request (FixtureRequest): fixture request object
          tmpdir_factory (py.path.local): fixture request object

        Returns:
          :obj:`py._path.local.LocalPath`: output directory in which the files reside
        """
        p = safe_mktemp(tmpdir_factory, fdir, **kwargs)
        for s, d in itertools.zip_longest(src, dst):
            safe_symlink(p, s, d)
        if request.config.option.ngs_show_fixture:
            logger.info("fileset fixture content")
            logger.info("-----------------------")
            for x in sorted(p.visit()):
                logger.info(str(x))
        return p
    return fileset_fixture


def application_output(application, command, version, end="se", **kwargs):
    """
    Fixture factory to generate application output.

    Params:
      application (str): application name
      command (str): application command name
      version (str): application version
      end (str): paired end or single end

    Returns:
      func: a filetype fixture function
    """
    from pytest_ngsfixtures.config import application_config
    conf = application_config()
    assert application in conf.keys(), "no such application '{}'".format(application)
    assert command in conf[application].keys(), "no such command '{}'".format(command)
    assert type(version) is str, "version must be string"
    if "_versions" in conf[application][command].keys():
        _versions = [str(x) for x in conf[application][command]["_versions"]]
    else:
        _versions = [str(x) for x in conf[application]["_versions"]]
    assert version in _versions, "no such application output for version '{}', application '{}'".format(version, application)
    assert end in ["se", "pe"], "end must be either se or pe"
    params = {'version': version, 'end': end}
    output = [x.format(**params) for x in conf[application][command]['output'].values()]
    if len(output) == 1:
        src = os.path.join("applications", application, output[0])
        return filetype(src, **kwargs)
    else:
        src = [os.path.join("applications", application, x) for x in output]
        return fileset(src, **kwargs)


__all__ = ('sample_layout', 'reference_layout', 'filetype', 'fileset')
