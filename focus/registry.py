""" This module provides a registry class for callables. This is used primarily
    as part of the plugin registration in the `registration` module.
    """

__all__ = ('Registry', 'ExtRegistry')


class Registry(object):
    """ Class that provides a basic hash-like container to manage and query for
        callables. This is useful for providing components a simple interface
        to lookup their respective handlers by a specific key.
        """

    def __init__(self):
        self._actions = {}
        self._cache = {}

    def __iter__(self):
        """ Returns iterable of key and cached value for key.
            """
        for key in self._actions.keys():
            yield key, self.get(key)

    def clear(self):
        """ Deregisters all keys and internal caching.
            """
        self._actions = {}
        self._cache = {}

    def get(self, key):
        """ Executes the callable registered at the specified key and returns
            its value. Subsequent queries are cached internally.

            `key`
                String key for a previously stored callable.
            """

        if not key in self._actions:
            return None
        if not key in self._cache:
            self._cache[key] = self._actions[key]()

        return self._cache[key]

    def register(self, key, value):
        """ Registers a callable with the specified key.

            `key`
                String key to identify a callable.
            `value`
                Callable object.
            """

        self._actions[key] = value

        # invalidate cache of results for existing key
        if key in self._cache:
            del self._cache[key]

    def deregister(self, key):
        """ Deregisters an existing key.

            `key`
                String key to deregister.

            Returns boolean.
            """

        if not key in self._actions:
            return False

        del self._actions[key]

        if key in self._cache:
            del self._cache[key]

        return True


class ExtRegistry(Registry):
    """ Extended Registry class that provides additional type information along
        with the callable being registered.
        """

    def __init__(self, *args, **kwargs):
        super(ExtRegistry, self).__init__(*args, **kwargs)
        self._type_info = {}

    def clear(self):
        """ Deregisters all keys and internal caching.
            """
        super(ExtRegistry, self).clear()
        self._type_info = {}

    def get(self, key):
        """ Executes the callable registered at the specified key and returns
            its value along with type info. Subsequent queries are cached
            internally.

            `key`
                String key for a previously stored callable.
            """

        obj = super(ExtRegistry, self).get(key)
        if obj is None:
            return obj

        return (obj, self._type_info.get(key))

    def register(self, key, value, type_info):
        """ Registers a callable with the specified key and type info.

            `key`
                String key to identify a callable.
            `value`
                Callable object.
            `type_info`
                Dictionary with type information about the value provided.
            """

        # check for existing action
        old_action = self._actions.get(key)

        # update existing type info if value hasn't changed
        if old_action == value and key in self._type_info:
            self._type_info[key].update(type_info)
        else:
            self._type_info[key] = dict(type_info)

        super(ExtRegistry, self).register(key, value)

    def deregister(self, key):
        """ Deregisters an existing key.

            `key`
                String key to deregister.

            Returns boolean.
            """

        res = super(ExtRegistry, self).deregister(key)
        if key in self._type_info:
            del self._type_info[key]
        return res
