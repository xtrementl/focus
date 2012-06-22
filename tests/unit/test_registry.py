from focus_unittest import FocusTestCase
from focus.registry import Registry, ExtRegistry


class TestRegistry(FocusTestCase):
    def setUp(self):
        super(TestRegistry, self).setUp()
        self.registry = Registry()

    def tearDown(self):
        self.registry = None
        super(TestRegistry, self).tearDown()

    def testEmpty___iter__(self):
        """ Registry.__iter__: returns empty list when registry empty.
            """
        self.assertEqual(list(x for x in self.registry), [])

    def testWithItems___iter__(self):
        """ Registry.__iter__: returns list of (key, callable return value)
            tuples.
            """
        self.registry._actions['foo'] = lambda: 'llama'
        self.registry._actions['bar'] = lambda: 'candy'
        self.assertEqual(list(self.registry),
            [('foo', 'llama'), ('bar', 'candy')])

    def test__clear(self):
        """ Registry.clear: removes all keys.
            """
        self.registry._actions['foo'] = lambda: 'blah'
        self.registry._cache['foo'] = 'blah'
        self.registry._actions['bar'] = lambda: 'blah2'

        self.registry.clear()
        self.assertNotIn('foo', self.registry._actions)
        self.assertNotIn('foo', self.registry._cache)
        self.assertNotIn('bar', self.registry._actions)

    def testExistKey__get(self):
        """ Registry.get: returns (key, callable return value) tuple for
            existing key.
            """
        self.registry._actions['foo'] = lambda: 'blah'
        self.assertEqual(self.registry.get('foo'), 'blah')

    def testNonExistKey__get(self):
        """ Registry.get: returns ``None`` for non-existent key.
            """
        self.assertIsNone(self.registry.get('non-exist'))

    def testNewKey__register(self):
        """ Registry.register: adds new key and value.
            """
        v = lambda: 'bar'
        self.registry.register('foo', v)
        self.assertEqual(self.registry._actions['foo'], v)

    def testExistKeyUpdate__register(self):
        """ Registry.register: updates value for existing key.
            """
        # set first key
        v = lambda: 'bar'
        self.registry.register('foo', v)
        self.assertEqual(self.registry._actions['foo'], v)

        # update value for same key
        v2 = lambda: 'llama'
        self.registry.register('foo', v2)
        self.assertEqual(self.registry._actions['foo'], v2)

    def testExistKey__deregister(self):
        """ Registry.deregister: existing key is removed.
            """
        self.registry._actions['foo'] = lambda: 'bar'
        self.registry._cache['foo'] = 'bar'
        self.assertTrue(self.registry.deregister('foo'))
        self.assertNotIn('foo', self.registry._actions)
        self.assertNotIn('foo', self.registry._cache)

    def testNonExistKey__deregister(self):
        """ Registry.deregister: non-existant key returns False.
            """
        self.assertFalse(self.registry.deregister('non-exist'))


class TestExtRegistry(FocusTestCase):
    def setUp(self):
        super(TestExtRegistry, self).setUp()
        self.registry = ExtRegistry()

    def tearDown(self):
        self.registry = None
        super(TestExtRegistry, self).tearDown()

    def test__clear(self):
        """ ExtRegistry.clear: removes all keys.
            """
        self.registry._actions['foo'] = lambda: 'blah'
        self.registry._cache['foo'] = 'blah'
        self.registry._type_info['foo'] = {'a': 1, 'b': 2}
        self.registry._actions['bar'] = lambda: 'blah2'
        self.registry._type_info['bar'] = {'a': 1, 'b': 2}

        self.registry.clear()
        self.assertNotIn('foo', self.registry._actions)
        self.assertNotIn('foo', self.registry._cache)
        self.assertNotIn('foo', self.registry._type_info)
        self.assertNotIn('bar', self.registry._actions)
        self.assertNotIn('bar', self.registry._type_info)

    def testExistKey__get(self):
        """ ExtRegistry.get: returns ((key, callable return value), type_dict)
            tuple for existing key.
            """
        self.registry._actions['foo'] = lambda: 'blah'
        t = {'a': 1, 'b': 2, 'c': 3}
        self.registry._type_info['foo'] = t
        self.assertEqual(self.registry.get('foo'), ('blah', t))

    def testNonExistKey__get(self):
        """ ExtRegistry.get: returns ``None`` for non-existent key.
            """
        self.assertIsNone(self.registry.get('non-exist'))

    def testNewKey__register(self):
        """ ExtRegistry.register: adds a new key.
            """
        v = lambda: 'bar'
        t = {'a': 1, 'b': 2, 'c': 3}
        self.registry.register('foo', v, t)
        self.assertEqual(self.registry._actions['foo'], v)
        self.assertEqual(self.registry._type_info['foo'], t)

    def testExistKeyUpdateType__register(self):
        """ ExtRegistry.register: updates type info for existing key.
            """
        # set first key
        v = lambda: 'bar'
        t = {'a': 1, 'b': 2, 'c': 3}
        self.registry.register('foo', v, t)
        self.assertEqual(self.registry._actions['foo'], v)
        self.assertEqual(self.registry._type_info['foo'], t)

        # update type info for same key
        t2 = {'a': 9, 'd': 4}
        t3 = t.copy()
        t3.update(t2)
        self.registry.register('foo', v, t2)
        self.assertEqual(self.registry._actions['foo'], v)
        self.assertEqual(self.registry._type_info['foo'], t3)

    def testExistKey__deregister(self):
        """ ExtRegistry.deregister: existing key is removed.
            """
        self.registry._actions['foo'] = lambda: 'bar'
        self.registry._cache['foo'] = 'bar'
        self.registry._type_info['foo'] = {'a': 1, 'b': 2, 'c': 3}
        self.assertTrue(self.registry.deregister('foo'))
        self.assertNotIn('foo', self.registry._actions)
        self.assertNotIn('foo', self.registry._type_info)
        self.assertNotIn('foo', self.registry._cache)

    def testNonExistKey__deregister(self):
        """ ExtRegistry.deregister: non-existant key returns ``False``.
            """
        self.assertFalse(self.registry.deregister('non-exist'))
