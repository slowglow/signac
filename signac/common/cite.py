# Copyright (c) 2016 The Regents of the University of Michigan
# All rights reserved.
# This software is licensed under the BSD 3-Clause License.
"""Functions to support citing this software."""
import sys


ARXIV_BIBTEX = """@online{signac,
    author      = {Carl S. Adorf and Paul M. Dodd and Sharon C. Glotzer},
    title       = {signac - A Simple Data Management Framework},
    year        = {2016},
    eprinttype  = {arxiv},
    eprintclass = {cs.DB},
    eprint      = {1611.03543}
}
"""


ARXIV_REFERENCE = "Carl S. Adorf, Paul M. Dodd, and Sharon C. Glotzer. signac - A SimpleData Management Framework. 2016. arXiv:1611.03543 [cs.DB]"


def bibtex(file=None):
    """Generate bibtex entries for signac.

    The bibtex entries will be printed to screen unless a
    filename or a file-like object are provided, in which
    case they will be stored in the corresponding file.

    .. note::

        A full reference should also include the
        version of this software. Please refer to the
        documentation on how to cite a specific version.

    :param file: A str or file-like object.
        Defaults to sys.stdout.
    """
    if file is None:
        file = sys.stdout
    elif isinstance(file, str):
        file = open(file, 'w')
    file.write(ARXIV_BIBTEX)


def reference(file=None):
    """Generate reference entries for signac.

    The references will be printed to screen unless a
    filename or a file-like object are provided, in which
    case they will be stored in the corresponding file.

    .. note::

        A full reference should also include the
        version of this software. Please refer to the
        documentation on how to cite a specific version.

    :param file: A str or file-like object.
        Defaults to sys.stdout.
    """
    if file is None:
        file = sys.stdout
    elif isinstance(file, str):
        file = open(file, 'w')
    file.write(ARXIV_REFERENCE + '\n')
