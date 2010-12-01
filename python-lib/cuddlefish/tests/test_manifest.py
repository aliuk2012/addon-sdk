
import os, re
import unittest
from StringIO import StringIO
from cuddlefish.manifest import scan_module, scan_package, \
     update_manifest_with_fileinfo

class Extra:
    def failUnlessKeysAre(self, d, keys):
        self.failUnlessEqual(sorted(d.keys()), sorted(keys))

class Require(unittest.TestCase, Extra):
    def scan(self, text):
        lines = StringIO(text).readlines()
        requires, chrome, problems = scan_module("fake.js", lines)
        self.failUnlessEqual(problems, False)
        return requires, chrome

    def test_modules(self):
        mod = """var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one"])
        self.failUnlessEqual(chrome, False)

        mod = """var foo = require(\"one\");"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one"])
        self.failUnlessEqual(chrome, False)

        mod = """var foo=require(  'one' )  ;  """
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one"])
        self.failUnlessEqual(chrome, False)

        mod = """var foo = require('o'+'ne'); // tricky, denied"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        mod = """require('one').immediately.do().stuff();"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one"])
        self.failUnlessEqual(chrome, False)

        # these forms are commented out, and thus ignored

        mod = """// var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        mod = """/* var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        mod = """ * var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        mod = """ ' var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        mod = """ \" var foo = require('one');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)

        # multiple requires

        mod = """const foo = require('one');
        const foo = require('two');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one", "two"])
        self.failUnlessEqual(chrome, False)

        mod = """const foo = require('one'); const foo = require('two');"""
        requires, chrome = self.scan(mod)
        self.failUnlessKeysAre(requires, ["one", "two"])
        self.failUnlessEqual(chrome, False)

def scan2(text, fn="fake.js"):
    stderr = StringIO()
    lines = StringIO(text).readlines()
    requires, chrome, problems = scan_module(fn, lines, stderr)
    stderr.seek(0)
    return requires, chrome, problems, stderr.readlines()

class Chrome(unittest.TestCase, Extra):

    def test_ignore_loader(self):
        # we specifically ignore the two loader files
        mod = """let {Cc,Ci} = require('chrome');"""
        requires, chrome, problems, err = scan2(mod, "blah/cuddlefish.js")
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

        mod = """let {Cc,Ci} = require('chrome');"""
        requires, chrome, problems, err = scan2(mod, "securable-module.js")
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

    def test_chrome(self):
        mod = """let {Cc,Ci} = require('chrome');"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, True)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

        mod = """var foo = require('foo');
        let {Cc,Ci} = require('chrome');"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, ["foo"])
        self.failUnlessEqual(chrome, True)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

        mod = """let c = require('chrome');"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, True)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

        mod = """var foo = require('foo');
        let c = require('chrome');"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, ["foo"])
        self.failUnlessEqual(chrome, True)
        self.failUnlessEqual(problems, False)
        self.failUnlessEqual(err, [])

class BadChrome(unittest.TestCase, Extra):
    def test_bad_alias(self):
        # using Components.* gets you a warning. If it looks like you're
        # using it to build an alias, the warning suggests a better way.
        mod = """let Cc = Components.classes;"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)
        self.failUnlessEqual(problems, True)
        self.failUnlessEqual(err[1], "To use chrome authority, as in:\n") 
        self.failUnlessEqual(err[-1], '  const {Cc} = require("chrome");\n')

    def test_bad_misc(self):
        # If it looks like you're using something that doesn't have an alias,
        # the warning also suggests a better way.
        mod = """if (Components.isSuccessCode(foo))"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)
        self.failUnlessEqual(problems, True)
        self.failUnlessEqual(err[1], "To use chrome authority, as in:\n") 
        self.failUnlessEqual(err[-1],
                             '  const {components} = require("chrome");\n')

        mod = """let CID = Components.ID""" # not one of the usual aliases
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, False)
        self.failUnlessEqual(problems, True)
        self.failUnlessEqual(err[1], "To use chrome authority, as in:\n") 
        self.failUnlessEqual(err[-1],
                             '  const {components} = require("chrome");\n')

    def test_use_too_much(self):
        # if you use more than you ask for, you also get a warning
        mod = """let {Cc,Ci} = require('chrome');
        Cu.something();"""
        requires, chrome, problems, err = scan2(mod)
        self.failUnlessKeysAre(requires, [])
        self.failUnlessEqual(chrome, True)
        self.failUnlessEqual(problems, True)
        err = "".join(err)
        self.failUnless("To use chrome authority, as in:" in err, err)
        self.failUnless("2> Cu.something()" in err, err)
        self.failUnless("You must enable it with something like:" in err, err)
        self.failUnless('const {Cc,Ci,Cu} = require("chrome");' in err, err)

class Package(unittest.TestCase):
    def test_e10s_adapter(self):
        path = "python-lib/cuddlefish/tests/e10s-adapter-files/packages/foo/lib"
        manifest, has_problems = scan_package("prefix-", "resource:foo/",
                                              "foo", "lib", path)
        update_manifest_with_fileinfo(["foo"], "foo", manifest)
        self.assertEqual(manifest['resource:foo/bar.js']['e10s-adapter'],
                         'resource:foo/bar-e10s-adapter.js')
        self.assertFalse(manifest['resource:foo/bar-e10s-adapter.js']['e10s-adapter'])
        self.assertFalse(manifest['resource:foo/foo.js']['e10s-adapter'])

    def test_bug_596573(self):
        jp_tests = "packages/api-utils/tests"
        manifest, has_problems = scan_package("prefix", "resource:foo",
                                              "api-utils", "tests", jp_tests)
        found = [i.name for i in manifest.values()
                 if i.name == "interoperablejs-read-only/compliance/" +
                               "nested/a/b/c/d"]
        self.failUnless(len(found) == 1)
        
    def test_jetpack_core(self):
        # this has a side-effect of asserting that all the SDK's api-utils
        # modules are clean.
        jp_core = "packages/api-utils/lib"
        assert os.path.isdir(jp_core) # we expect to be run from the SDK top
        stderr = StringIO()
        manifest, has_problems = scan_package("prefix-", "resource:foo/",
                                              "api-utils", "lib",
                                              jp_core, stderr)
        stderr.seek(0)
        err = stderr.readlines()
        self.failUnlessEqual(err, [], "".join(err))
        self.failUnlessEqual(has_problems, False)
        update_manifest_with_fileinfo(["api-utils"], "api-utils",
                                      manifest)

        # look at a few samples from the manifest: this depends upon the
        # behavior of other files in the SDK, so when those files change
        # (specifically when they move or add dependencies), this test must
        # be updated
        self.failUnless("resource:foo/tab-browser.js" in manifest, manifest.keys())
        tb = manifest["resource:foo/tab-browser.js"]
        self.failUnlessEqual(tb.chrome, True)
        self.failUnlessEqual(tb.name, "tab-browser")
        self.failUnlessEqual(tb.packageName, "api-utils")
        self.failUnless("window-utils" in tb.requires, tb.requires.values())
        self.failUnlessEqual(tb.requires["window-utils"].url,
                             "resource:foo/window-utils.js")
        self.failUnlessEqual(tb.sectionName, "lib")
        self.failUnlessEqual(tb.zipname,
                             "resources/prefix-api-utils-lib/tab-browser.js")
        h = tb.hash
        self.failUnless(re.search(r'^[0-9a-f]{64}$', h), h)
        # don't assert the actual value, since that will change each time
        # page-mod.js changes

        self.failUnless("resource:foo/api-utils.js" in manifest, manifest.keys())

if __name__ == '__main__':
    unittest.main()
