"""
Original module from Cesar Saez
https://github.com/csaez/naming

"""

import tempfile
import unittest
import naming as n


class SolveCase(unittest.TestCase):
    def setUp(self):
        n.flush_tokens()
        n.add_token("description")
        n.add_token("side", left="L", right="R", middle="M", default="M")
        n.add_token("type", animation="anim", control="ctrl", joint="jnt", default="ctrl")

        n.flush_rules()
        n.add_rule("test1", "description", "side", "type")
        n.add_rule("test2", "side", "description")
        n.set_active_rule("test1")

    def test_explicit(self):
        name = "foo_L_anim"
        solved = n.solve(description="foo", side="left", type="animation")
        self.assertEqual(solved, name)

        name = "foo_M_anim"
        solved = n.solve(description="foo", side="middle", type="animation")
        self.assertEqual(solved, name)

        n.set_active_rule("test2")

        name = "L_foo"
        solved = n.solve(description="foo", side="left", type="animation")
        self.assertEqual(solved, name)

        name = "M_foo"
        solved = n.solve(description="foo", side="middle", type="animation")
        self.assertEqual(solved, name)

    def test_defaults(self):
        name = "foo_M_anim"
        solved = n.solve(description="foo", type="animation")
        self.assertEqual(solved, name)

        name = "foo_M_ctrl"
        solved = n.solve(description="foo")
        self.assertEqual(solved, name)

        n.set_active_rule("test2")

        name = "M_foo"
        solved = n.solve(description="foo", type="animation")
        self.assertEqual(solved, name)

        solved = n.solve(description="foo")
        self.assertEqual(solved, name)

    def test_implicit(self):
        name = "foo_M_anim"
        solved = n.solve("foo", type="animation")
        self.assertEqual(solved, name)

        name = "foo_M_ctrl"
        solved = n.solve("foo")
        self.assertEqual(solved, name)

        n.set_active_rule("test2")

        name = "M_foo"
        solved = n.solve("foo", type="animation")
        self.assertEqual(solved, name)

        name = "M_foo"
        solved = n.solve("foo")
        self.assertEqual(solved, name)


class ParseCase(unittest.TestCase):
    def setUp(self):
        n.flush_tokens()
        n.add_token("description")
        n.add_token("side", left="L", right="R", middle="M", default="M")
        n.add_token("type", animation="anim", control="ctrl", joint="jnt", default="ctrl")

        n.flush_rules()
        n.add_rule("test1", "description", "side", "type")
        n.add_rule("test2", "side", "description")
        n.set_active_rule("test1")

    def test_parsing(self):
        name = "foo_M_ctrl"
        parsed = n.parse(name)
        self.assertEqual(parsed["description"], "foo")
        self.assertEqual(parsed["side"], "middle")
        self.assertEqual(parsed["type"], "control")
        self.assertEqual(len(parsed), 3)

        n.set_active_rule("test2")

        name = "M_foo"
        parsed = n.parse(name)
        self.assertEqual(parsed["description"], "foo")
        self.assertEqual(parsed["side"], "middle")
        self.assertEqual(len(parsed), 2)


class TokenCase(unittest.TestCase):
    def setUp(self):
        n.flush_tokens()

    def test_add(self):
        result = n.add_token("description")
        self.assertTrue(result)

        result = n.add_token("side", left="L", right="R", middle="M", default="M")
        self.assertTrue(result)

    def test_flush(self):
        result = n.flush_tokens()
        self.assertTrue(result)

    def test_remove(self):
        n.add_token("test")
        result = n.remove_token("test")
        self.assertTrue(result)

        result = n.remove_token("test2")
        self.assertFalse(result)

    def test_has(self):
        name = "foo"
        n.add_token(name)
        r = n.has_token(name)
        self.assertTrue(r)

        n.remove_token(name)
        r = n.has_token(name)
        self.assertFalse(r)

class RuleCase(unittest.TestCase):
    def setUp(self):
        n.flush_rules()

    def test_add(self):
        result = n.add_rule("test", "description", "side", "type")
        self.assertTrue(result)

    def test_flush(self):
        result = n.flush_rules()
        self.assertTrue(result)

    def test_remove(self):
        n.add_rule("test", "description", "side", "type")
        result = n.remove_rule("test")
        self.assertTrue(result)

        result = n.remove_rule("test2")
        self.assertFalse(result)

    def test_has(self):
        name = "foo"
        n.add_rule(name, "description", "side", "type")
        r = n.has_rule(name)
        self.assertTrue(r)

        n.remove_rule(name)
        r = n.has_rule(name)
        self.assertFalse(r)

    def test_active(self):
        name = "foo"
        n.add_rule(name, "description", "side", "type")
        r = n.active_rule()
        self.assertIsNotNone(r)


class SerializationCase(unittest.TestCase):
    def setUp(self):
        n.flush_rules()
        n.flush_tokens()

    def test_tokens(self):
        token1 = n.add_token("side", left="L", right="R", middle="M", default="M")
        token2 = n.Token.from_data(token1.data())
        self.assertEqual(token1.data(), token2.data())

    def test_rules(self):
        rule1 = n.add_rule("test", "description", "side", "type")
        rule2 = n.Rule.from_data(rule1.data())
        self.assertEqual(rule1.data(), rule2.data())

    def test_validation(self):
        token = n.add_token("side", left="L", right="R", middle="M", default="M")
        rule = n.add_rule("test", "description", "side", "type")
        self.assertIsNone(n.Rule.from_data(token.data()))
        self.assertIsNone(n.Token.from_data(rule.data()))

    def test_save_load_rule(self):
        n.add_rule("test", "description", "side", "type")
        filepath = tempfile.mktemp()
        n.save_rule("test", filepath)

        n.flush_rules()
        n.load_rule(filepath)
        self.assertTrue(n.has_rule("test"))

    def test_save_load_token(self):
        n.add_token("test", left="L", right="R", middle="M", default="M")
        filepath = tempfile.mktemp()
        n.save_token("test", filepath)

        n.flush_tokens()
        n.load_token(filepath)
        self.assertTrue(n.has_token("test"))

    def test_save_load_session(self):
        n.add_token("description")
        n.add_token("side", left="L", right="R", middle="M", default="M")
        n.add_token("type", animation="anim", control="ctrl", joint="jnt", default="ctrl")
        n.add_rule("test1", "description", "side", "type")
        n.add_rule("test2", "side", "description")
        n.set_active_rule("test1")

        repo = tempfile.mkdtemp()
        n.save_session(repo)

        n.flush_rules()
        n.flush_tokens()

        n.load_session(repo)
        self.assertTrue(n.has_token("description"))
        self.assertTrue(n.has_token("side"))
        self.assertTrue(n.has_token("type"))
        self.assertTrue(n.has_rule("test1"))
        self.assertTrue(n.has_rule("test2"))
        self.assertEqual(n.active_rule().name(), "test1")


if __name__ == "__main__":
    unittest.main()
