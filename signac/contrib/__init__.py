import os
import re
import logging
import json
import uuid
import importlib
import itertools

from .project import Project
from . import conversion
from . import formats
from .utility import walkdepth
from .hashing import generate_hash_from_spec

logger = logging.getLogger(__name__)

KEY_CRAWLER_PATH = 'signac_access_crawler_root'
KEY_CRAWLER_MODULE = 'signac_access_module'
KEY_CRAWLER_ID = 'signac_access_crawler_id'
KEY_PROJECT = 'project'
KEY_FILENAME = 'filename'
KEY_PATH = 'root'
KEY_PAYLOAD = 'format'
FN_CRAWLER = 'signac_access.py'


def get_project(project_path=None):
    if project_path is not None:
        cwd = os.getcwd()
        os.chdir(project_path)
        project = Project()
        os.chdir(cwd)
    else:
        project = Project()
    project.get_id()  # sanity check
    return project


class SimpleCollection(object):

    def __init__(self):
        self._index = dict()

    def insert_one(self, doc):
        _id = doc.setdefault('_id', uuid.uuid4())
        self._index[_id] = doc

    def insert_many(self, docs):
        for doc in docs:
            self.insert_one(doc)

    def replace_one(self, filter, doc):
        if not list(filter.keys()) == ['_id']:
            raise NotImplementedError(
                "Simple collection can only be queried for _id.")
        self._index[filter['_id']] = doc

    def find(self, limit=0):
        if limit != 0:
            yield from itertools.islice(self._index.values(), limit)
        else:
            yield from self._index.values()

    def find_one(self):
        return next(self._index.values())


class BaseCrawler(object):

    def __init__(self, root):
        self.root = root

    def docs_from_file(self, dirpath, fn):
        raise NotImplementedError()

    def fetch(self, doc):
        return
        yield

    @classmethod
    def calculate_hash(cls, doc, dirpath, fn):
        import hashlib
        blob = json.dumps(doc, sort_keys=True)
        m = hashlib.md5()
        m.update(dirpath.encode('utf-8'))
        m.update(fn.encode('utf-8'))
        m.update(blob.encode('utf-8'))
        return m.hexdigest()

    def crawl(self, depth=0):
        logger.info("Crawling '{}' (depth={})...".format(self.root, depth))
        for dirpath, dirnames, filenames in walkdepth(self.root, depth):
            for fn in filenames:
                for doc in self.docs_from_file(dirpath, fn):
                    logger.debug("doc from file: '{}'.".format(
                        os.path.join(dirpath, fn)))
                    doc.setdefault(KEY_PAYLOAD, None)
                    _id = doc.setdefault(
                        '_id', self.calculate_hash(doc, dirpath, fn))
                    yield _id, doc
        logger.info("Crawl of '{}' done.".format(self.root))

    def process(self, doc, dirpath, fn):
        return doc


class RegexFileCrawler(BaseCrawler):
    definitions = dict()

    @classmethod
    def define(cls, regex, format_):
        cls.definitions[regex] = format_

    def docs_from_file(self, dirpath, fn):
        for regex, format_ in self.definitions.items():
            m = regex.search(os.path.join(dirpath, fn))
            if m:
                doc = self.process(m.groupdict(), dirpath, fn)
                doc[KEY_FILENAME] = os.path.relpath(
                    os.path.join(dirpath, fn), self.root)
                doc[KEY_PATH] = os.path.abspath(self.root)
                doc[KEY_PAYLOAD] = str(format_)
                yield doc

    def fetch(self, doc):
        fn = doc.get(KEY_FILENAME)
        if fn:
            for regex, format_ in self.definitions:
                ffn = os.path.join(self.root, fn)
                m = regex.search(ffn)
                if m:
                    yield format_(open(ffn))

    def process(self, doc, dirpath, fn):
        result = dict()
        types = (int, float)
        for key, value in doc.items():
            for t in types:
                try:
                    result[key] = t(value)
                except ValueError:
                    continue
                else:
                    break
            else:
                result[key] = value
        return super().process(result, dirpath, fn)


class JSONCrawler(BaseCrawler):
    encoding = 'utf-8'
    fn_regex = '.*\.json'

    def docs_from_json(self, doc):
        yield doc

    def docs_from_file(self, dirpath, fn):
        if re.match(self.fn_regex):
            with open(os.path.join(dirpath, fn), 'rb') as file:
                doc = json.loads(file.read().decode(self.encoding))
                yield from self.docs_from_json(doc)


class SignacProjectCrawler(RegexFileCrawler):
    encoding = 'utf-8'
    fn_statepoint = 'signac_statepoint.json'
    re_jd = '.*signac_job_document\.json'

    def get_statepoint(self, dirpath):
        with open(os.path.join(dirpath, self.fn_statepoint), 'rb') as file:
            doc = json.loads(file.read().decode(self.encoding))
        signac_id = generate_hash_from_spec(doc)
        assert dirpath.endswith(signac_id)
        return signac_id, doc

    def process(self, doc, dirpath, fn):
        signac_id, statepoint = self.get_statepoint(dirpath)
        doc.update(statepoint)
        doc['signac_id'] = signac_id
        return super().process(doc, dirpath, fn)

    def docs_from_file(self, dirpath, fn):
        if re.match(self.re_jd, fn):
            with open(os.path.join(dirpath, fn), 'rb') as file:
                job_doc = json.loads(file.read().decode(self.encoding))
            signac_id, statepoint = self.get_statepoint(dirpath)
            job_doc['_id'] = signac_id
            job_doc['signac_id'] = signac_id
            job_doc['statepoint'] = statepoint
            job_doc[KEY_PAYLOAD] = 'signac_job_document'
            yield job_doc
        yield from super().docs_from_file(dirpath, fn)


class ProjectCrawler(BaseCrawler):

    def __init__(self, root):
        super(ProjectCrawler, self).__init__(root=root)
        self._crawlers = dict()

    def _load_crawler(self, name):
        return importlib.machinery.SourceFileLoader(name, name).load_module()

    def docs_from_file(self, dirpath, fn):
        if fn == FN_CRAWLER:
            name = os.path.join(dirpath, fn)
            module = self._load_crawler(name)
            for crawler_id, crawler in module.get_crawlers(dirpath).items():
                for _id, doc in crawler.crawl():
                    doc.setdefault(
                        KEY_PROJECT, os.path.relpath(dirpath, self.root))
                    doc[KEY_CRAWLER_PATH] = os.path.abspath(dirpath)
                    doc[KEY_CRAWLER_MODULE] = fn
                    doc[KEY_CRAWLER_ID] = crawler_id
                    yield doc

    def fetch(self, doc):
        yield from fetch(doc)


def _load_crawler(name):
    return importlib.machinery.SourceFileLoader(name, name).load_module()


def fetch(doc):
    fn_module = os.path.join(doc[KEY_CRAWLER_PATH], doc[KEY_CRAWLER_MODULE])
    try:
        crawler_module = _load_crawler(fn_module)
        crawlers = crawler_module.get_crawlers(doc[KEY_CRAWLER_PATH])
        yield from crawlers[doc[KEY_CRAWLER_ID]].fetch(doc)
    except KeyError:
        raise KeyError(
            "Unable to load crawler, associated with this document.")


def fetched(docs):
    for doc in docs:
        for data in fetch(doc):
            yield doc, data


class ConversionNetwork(object):

    def __init__(self, formats_network):
        self.formats_network = formats_network

    def convert(self, src, target_format, debug=False):
        return conversion.convert(src, target_format, self.formats_network, debug=debug)

    def converted(self, sources, target_format, ignore_errors=True):
        yield from conversion.converted(sources, target_format, self.formats_network, ignore_errors=ignore_errors)


def export_pymongo(crawler, collection, chunksize=1000, *args, **kwargs):
    import pymongo
    logger.info("Exporting index for pymongo.")
    operations = []
    for _id, doc in crawler.crawl(*args, **kwargs):
        f = {'_id': _id}
        assert doc['_id'] == _id
        operations.append(pymongo.ReplaceOne(f, doc, upsert=True))
        if len(operations) >= chunksize:
            logger.debug("Pushing chunk.")
            collection.bulk_write(operations)
            operations.clear()
    if len(operations):
        logger.debug("Pushing final chunk.")
        collection.bulk_write(operations)


def export(crawler, collection, *args, **kwargs):
    logger.info("Exporting index.")
    for _id, doc in crawler.crawl(*args, **kwargs):
        f = {'_id': _id}
        collection.replace_one(f, doc)


def get_formats_network():
    import networkx as nx
    """Generate a formats network from all registered formats and adapters.
    Every adapter in the global namespace is automatically registered.
    """
    network = nx.DiGraph()
    network.add_nodes_from(formats.BASICS)
    network.add_nodes_from(formats.BasicFormat.registry.values())
    for adapter in conversion.Adapter.registry.values():
        logger.debug("Adding '{}' to network.".format(adapter()))
        conversion.add_adapter_to_network(
            network, adapter)
    return network


def get_conversion_network():
    return ConversionNetwork(get_formats_network())
