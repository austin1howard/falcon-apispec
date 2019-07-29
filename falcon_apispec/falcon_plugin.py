"""
Note that while this works, it's a hacky solution. I've got a PR in progress with the apispec team for "proper" falcon support.
"""

import copy
from collections import defaultdict

from apispec import BasePlugin, yaml_utils
from apispec.exceptions import APISpecError
import falcon


class FalconPlugin(BasePlugin):
    """APISpec plugin for Falcon"""

    def __init__(self, app):
        super(FalconPlugin, self).__init__()
        self._app = app

    def path_helper(self, path, operations, resource, suffix = None, **kwargs):
        """Path helper that allows passing a Falcon resource instance."""
        path = None
        methods = {}

        routes_to_check = copy.copy(self._app._router._roots)

        for route in routes_to_check:
            routes_to_check.extend(route.children)

        operations.update(yaml_utils.load_operations_from_docstring(resource.__doc__) or {})

        for route in routes_to_check:
            if route.resource == resource:
                # found a match
                if path and not suffix:
                    raise APISpecError("Suffix required when multiple paths route to resource")

                method_map = route.method_map

                if suffix:
                    # see if this set of methods ends with the provided suffix.
                    for verb, method in method_map.items():
                        method_name: str = method.__name__
                        if method_name in ['method_not_allowed', 'on_options']:
                            continue  # not an implemented verb

                        if method_name.endswith(suffix):
                            # match. Make sure that we either don't have a path, or we have the same path
                            if not path or path == route.uri_template:
                                path = route.uri_template
                                methods[verb.lower()] = method_name
                            else:
                                raise APISpecError("suffix routed to multiple paths somehow")
                else:
                    for verb, method in method_map.items():
                        method_name: str = method.__name__
                        if method_name in ['method_not_allowed', 'on_options']:
                            continue  # not an implemented verb
                        path = route.uri_template
                        methods[verb.lower()] = method_name

        if not path:
            raise APISpecError("Could not find endpoint for resource {0}".format(resource))

        for http_verb, method_name in methods.items():
            if getattr(resource, method_name, None) is not None:
                method = getattr(resource, method_name)
                docstring_yaml = yaml_utils.load_yaml_from_docstring(method.__doc__)
                operations[http_verb] = docstring_yaml or dict()

        return path
