from pyramid.scaffolds import PyramidTemplate
import binascii
import os
from os import urandom, chdir
import subprocess


class RamsesStarterTemplate(PyramidTemplate):
    _template_dir = 'ramses_starter'
    summary = 'Ramses starter'

    def pre(self, command, output_dir, vars):
        vars['engine'] = raw_input("""
        Which DB backend would you like to use (either 'sqla' or 'mongodb')?:
        """)
        vars['random_string'] = binascii.hexlify(os.urandom(20))
        if vars['package'] == 'site':
            raise ValueError("""
                "Site" is a reserved keyword in Python.
                 Please use a different project name. """)

    def post(self, command, output_dir, vars):
        os.chdir(str(output_dir))
        subprocess.call("pip install -r requirements.txt", shell=True)
        msg = """Goodbye boilerplate! Welcome to Ramses."""
        self.out(msg)

