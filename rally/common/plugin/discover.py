# Copyright 2015: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import imp
import os
import pkg_resources
import pkgutil
import sys

from oslo_utils import importutils
import six

import rally
from rally.common.i18n import _
from rally.common import logging

LOG = logging.getLogger(__name__)


def itersubclasses(cls, seen=None):
    """Generator over all subclasses of a given class in depth first order."""

    seen = seen or set()
    try:
        subs = cls.__subclasses__()
    except TypeError:   # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in seen:
            seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, seen):
                yield sub


def import_modules_from_package(package):
    """Import modules from package and append into sys.modules

    :param package: Full package name. For example: rally.deployment.engines
    """
    path = [os.path.dirname(rally.__file__), ".."] + package.split(".")
    path = os.path.join(*path)
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.startswith("__") or not filename.endswith(".py"):
                continue
            new_package = ".".join(root.split(os.sep)).split("....")[1]
            module_name = "%s.%s" % (new_package, filename[:-3])
            if module_name not in sys.modules:
                sys.modules[module_name] = importutils.import_module(
                    module_name)


def import_modules_by_entry_point():
    """Import plugins by entry-point 'rally_plugins'."""
    for ep in pkg_resources.iter_entry_points("rally_plugins"):
        if ep.name == "path":
            try:
                m = ep.load()
                if hasattr(m, "__path__"):
                    path = pkgutil.extend_path(m.__path__, m.__name__)
                else:
                    path = m.__file__
                prefix = m.__name__ + "."
                for loader, name, _is_pkg in pkgutil.walk_packages(
                        path, prefix=prefix):
                    mod = loader.find_module(name).load_module(name)
                    sys.modules[name] = mod
            except Exception as e:
                LOG.warning(
                    "\t Failed to load plugins from module '%(module)s' "
                    "(package: '%(package)s'): '%(error)s')" % {
                        "module": ep.module_name,
                        "package": "%s %s" % (ep.dist.project_name,
                                              ep.dist.version),
                        "error": six.text_type(e)
                    })
                if logging.is_debug():
                    LOG.exception(e)


def load_plugins(dir_or_file):
    if os.path.isdir(dir_or_file):
        directory = dir_or_file
        LOG.info(_("Loading plugins from directories %s/*") %
                 directory.rstrip("/"))

        to_load = []
        for root, dirs, files in os.walk(directory, followlinks=True):
            to_load.extend((plugin[:-3], root)
                           for plugin in files if plugin.endswith(".py"))
        for plugin, directory in to_load:
            if directory not in sys.path:
                sys.path.append(directory)

            fullpath = os.path.join(directory, plugin)
            try:
                fp, pathname, descr = imp.find_module(plugin, [directory])
                imp.load_module(plugin, fp, pathname, descr)
                fp.close()
                LOG.info(_("\t Loaded module with plugins: %s.py") % fullpath)
            except Exception as e:
                LOG.warning(
                    "\t Failed to load module with plugins %(path)s.py: %(e)s"
                    % {"path": fullpath, "e": e})
                if logging.is_debug():
                    LOG.exception(e)
    elif os.path.isfile(dir_or_file):
        plugin_file = dir_or_file
        LOG.info(_("Loading plugins from file %s") % plugin_file)
        if plugin_file not in sys.path:
            sys.path.append(plugin_file)
        try:
            plugin_name = os.path.splitext(plugin_file.split("/")[-1])[0]
            imp.load_source(plugin_name, plugin_file)
            LOG.info(_("\t Loaded module with plugins: %s.py") % plugin_name)
        except Exception as e:
            LOG.warning(_(
                "\t Failed to load module with plugins %(path)s: %(e)s")
                % {"path": plugin_file, "e": e})
            if logging.is_debug():
                LOG.exception(e)
