"""
Original module from Cesar Saez
https://github.com/csaez/naming

"""
# Stdlib imports
from __future__ import absolute_import
import os
import json
import copy

NAMING_REPO_ENV = "NAMING_REPO"
_tokens = dict()
_rules = {"_active": None}


class Serializable(object):

    def data(self):
        retval = copy.deepcopy(self.__dict__)
        retval["_Serializable_classname"] = type(self).__name__
        retval["_Serializable_version"] = "1.0"
        return retval

    @classmethod
    def from_data(cls, data):
        if data.get("_Serializable_classname") != cls.__name__:
            return None
        del data["_Serializable_classname"]
        if data.get("_Serializable_version") is not None:
            del data["_Serializable_version"]

        this = cls(None)
        this.__dict__.update(data)
        return this


class Token(Serializable):

    def __init__(self, name):
        super(Token, self).__init__()
        self._name = name
        self._default = None
        self._items = dict()

    def name(self):
        return self._name

    def set_default(self, value):
        self._default = value

    def default(self):
        if self._default is None and len(self._items):
            self._default = self._items.values()[0]
        return self._default

    def add_item(self, name, value):
        self._items[name] = value

    def is_required(self):
        return self.default() is None

    def solve(self, name=None):
        if name is None:
            return self.default()
        return self._items.get(name)

    def parse(self, value):
        for k, v in self._items.iteritems():
            if v == value:
                return k


class Rule(Serializable):

    def __init__(self, name):
        super(Rule, self).__init__()
        self._name = name
        self._fields = list()

    def name(self):
        return self._name

    def fields(self):
        return tuple(self._fields)

    def add_fields(self, token_names):
        self._fields.extend(token_names)
        return True

    def _pattern(self):
        return "{{{}}}".format("}_{".join(self._fields))

    def solve(self, **values):
        return self._pattern().format(**values)

    def parse(self, name):
        retval = dict()
        split_name = name.split("_")
        for i, f in enumerate(self.fields()):
            value = split_name[i]
            token = _tokens[f]
            if token.is_required():
                retval[f] = value
                continue
            retval[f] = token.parse(value)
        return retval


def add_rule(name, *fields):
    rule = Rule(name)
    rule.add_fields(fields)
    _rules[name] = rule
    if active_rule() is None:
        set_active_rule(name)
    return rule


def flush_rules():
    _rules.clear()
    _rules["_active"] = None
    return True


def remove_rule(name):
    if has_rule(name):
        del _rules[name]
        return True
    return False


def has_rule(name):
    return name in _rules.keys()


def active_rule():
    k = _rules["_active"]
    return _rules.get(k)


def set_active_rule(name):
    if not has_rule(name):
        return False
    _rules["_active"] = name
    return True


def get_rule(name):
    return _rules.get(name)


def save_rule(name, filepath):
    rule = get_rule(name)
    if not rule:
        return False
    with open(filepath, "w") as fp:
        json.dump(rule.data(), fp)
    return True


def load_rule(filepath):
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath) as fp:
            data = json.load(fp)
    except:
        return False
    rule = Rule.from_data(data)
    _rules[rule.name()] = rule
    return True


def add_token(name, **kwds):
    token = Token(name)
    for k, v in kwds.iteritems():
        if k == "default":
            token.set_default(v)
            continue
        token.add_item(k, v)
    _tokens[name] = token
    return token


def flush_tokens():
    _tokens.clear()
    return True


def remove_token(name):
    if has_token(name):
        del _tokens[name]
        return True
    return False


def has_token(name):
    return name in _tokens.keys()


def get_token(name):
    return _tokens.get(name)


def save_token(name, filepath):
    token = get_token(name)
    if not token:
        return False
    with open(filepath, "w") as fp:
        json.dump(token.data(), fp)
    return True


def load_token(filepath):
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath) as fp:
            data = json.load(fp)
    except:
        return False
    token = Token.from_data(data)
    _tokens[token.name()] = token
    return True


def solve(*args, **kwds):
    i = 0
    values = dict()
    rule = active_rule()
    for f in rule.fields():
        token = _tokens[f]
        if token.is_required():
            if kwds.get(f) is not None:
                values[f] = kwds[f]
                continue
            values[f] = args[i]
            i += 1
            continue
        values[f] = token.solve(kwds.get(f))
    return rule.solve(**values)


def parse(name):
    rule = active_rule()
    return rule.parse(name)


def get_repo():
    env_repo = os.environ.get(NAMING_REPO_ENV)
    local_repo = os.path.join(os.path.expanduser("~"), ".config", "naming")
    return env_repo or local_repo


def save_session(repo=None):
    repo = repo or get_repo()
    if not os.path.exists(repo):
        os.mkdir(repo)
    # tokens and rules
    for name, token in _tokens.iteritems():
        filepath = os.path.join(repo, name + ".token")
        save_token(name, filepath)
    for name, rule in _rules.iteritems():
        if not isinstance(rule, Rule):
            continue
        filepath = os.path.join(repo, name + ".rule")
        save_rule(name, filepath)
    # extra configuration
    active = active_rule()
    config = {"set_active_rule": active.name() if active else None}
    filepath = os.path.join(repo, "naming.conf")
    with open(filepath, "w") as fp:
        json.dump(config, fp)
    return True


def load_session(repo=None):
    repo = repo or get_repo()
    # tokens and rules
    for dirpath, dirnames, filenames in os.walk(repo):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if filename.endswith(".token"):
                load_token(filepath)
            elif filename.endswith(".rule"):
                load_rule(filepath)
    # extra configuration
    filepath = os.path.join(repo, "naming.conf")
    if os.path.exists(filepath):
        with open(filepath) as fp:
            config = json.load(fp)
        for k, v in config.iteritems():
            globals()[k](v)
    return True
