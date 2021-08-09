# Copyright (c) 2017 The Regents of the University of Michigan
# All rights reserved.
# This software is licensed under the BSD 3-Clause License.
"""Parses signac config files."""

import logging
import os

from ..common.deprecation import deprecated
from ..version import __version__
from .configobj import ConfigObj, ConfigObjError
from .errors import ConfigError
from .validate import cfg, get_validator

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = ".signacrc"
CONFIG_FILENAMES = [DEFAULT_FILENAME, "signac.rc"]
HOME = os.path.expanduser("~")
CONFIG_PATH = [HOME]
FN_CONFIG = os.path.expanduser("~/.signacrc")


def _search_local(root):
    for fn in CONFIG_FILENAMES:
        fn_ = os.path.abspath(os.path.join(root, fn))
        if os.path.isfile(fn_):
            yield fn_


def _search_tree(root=None):
    """Locates signac configuration files in a directory hierarchy.

    Parameters
    ----------
    root : str
        Path to search. Uses ``os.getcwd()`` if None (Default value = None).

    """
    if root is None:
        root = os.getcwd()
    while True:
        yield from _search_local(root)
        up = os.path.abspath(os.path.join(root, ".."))
        if up == root:
            msg = "Reached filesystem root."
            logger.debug(msg)
            return
        else:
            root = up


def _search_standard_dirs():
    """Locates signac configuration files in standard directories."""
    for path in CONFIG_PATH:
        yield from _search_local(path)


@deprecated(
    deprecated_in="1.8",
    removed_in="2.0",
    current_version=__version__,
    details="The search_standard_dirs method is deprecated.",
)
def search_standard_dirs():  # noqa: D103
    yield from _search_standard_dirs()


def _read_config_file(filename):
    logger.debug(f"Reading config file '{filename}'.")
    try:
        config = Config(filename, configspec=cfg.split("\n"))
    except (OSError, ConfigObjError) as error:
        msg = "Failed to read configuration file '{}':\n{}"
        raise ConfigError(msg.format(filename, error))
    verification = config.verify()
    if verification is not True:
        logger.debug(
            "Config file '{}' may contain invalid values.".format(
                os.path.abspath(filename)
            )
        )
    return config


@deprecated(
    deprecated_in="1.8",
    removed_in="2.0",
    current_version=__version__,
    details=(
        "The read_config_file method is deprecated. Configs should only be "
        "accessed via a Project instance.",
    ),
)
def read_config_file(filename):
    """Read a configuration file."""
    return _read_config_file(filename)


def _get_config(infile=None, configspec=None, *args, **kwargs):
    """Get configuration from a file."""
    if configspec is None:
        configspec = cfg.split("\n")
    return Config(infile, configspec=configspec, *args, **kwargs)


@deprecated(
    deprecated_in="1.8",
    removed_in="2.0",
    current_version=__version__,
    details=(
        "The get_config method is deprecated. Configs should only be "
        "accessed via a Project instance.",
    ),
)
def get_config(infile=None, configspec=None, *args, **kwargs):  # noqa: D103
    """Get configuration from a file."""
    return _get_config(infile, configspec, *args, **kwargs)


def _load_config(root=None, local=False):
    """Load configuration, searching upward from a root path."""
    if root is None:
        root = os.getcwd()
    config = Config(configspec=cfg.split("\n"))
    if local:
        for fn in _search_local(root):
            tmp = _read_config_file(fn)
            config.merge(tmp)
            if "project" in tmp:
                config["project_dir"] = os.path.dirname(fn)
                break
    else:
        for fn in _search_standard_dirs():
            config.merge(_read_config_file(fn))
        for fn in _search_tree(root):
            tmp = _read_config_file(fn)
            config.merge(tmp)
            if "project" in tmp:
                config["project_dir"] = os.path.dirname(fn)
                break
    return config


@deprecated(
    deprecated_in="1.8",
    removed_in="2.0",
    current_version=__version__,
    details=(
        "The load_config method is deprecated. Configs should only be "
        "accessed via a Project instance.",
    ),
)
def load_config(root=None, local=False):
    """Load configuration, searching upward from a root path."""
    return _load_config(root, local)


class Config(ConfigObj):
    """Manages configuration for a signac project."""

    encoding = "utf-8"

    def verify(self, validator=None, *args, **kwargs):
        """Validate the contents of this configuration."""
        if validator is None:
            validator = get_validator()
        return super().validate(validator, *args, **kwargs)
