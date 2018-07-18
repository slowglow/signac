# Copyright (c) 2017 The Regents of the University of Michigan
# All rights reserved.
# This software is licensed under the BSD 3-Clause License.
from ..core.errors import Error


class WorkspaceError(Error, OSError):
    "Raised when there is an issue to create or access the workspace."
    def __init__(self, error):
        self.error = error
        "The underlying error causing this issue."

    def __str__(self):
        return self.error


class DestinationExistsError(Error, RuntimeError):
    "The destination for a move or copy operation already exists."
    def __init__(self, destination):
        self.destination = destination
        "The destination object causing the error."


class JobsCorruptedError(Error, RuntimeError):
    "The state point manifest file of one or more jobs cannot be openend or is corrupted."
    def __init__(self, job_ids):
        self.job_ids = job_ids
        "The job id(s) of the corrupted job(s)."


class SchemaPathMismatchError(Error, RuntimeError):
    "The state point provided by the manifest file does not match the one parsed from the path."
    def __init__(self, path, sp_from_manifest, sp_from_path):
        self.path = path
        self.sp_from_manifest = sp_from_manifest
        self.sp_from_path = sp_from_path

    def __str__(self):
        return super().__str__()
