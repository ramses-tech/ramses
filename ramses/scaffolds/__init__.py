import os
import subprocess

from six import moves
from pyramid.scaffolds import PyramidTemplate


class RamsesStarterTemplate(PyramidTemplate):
    _template_dir = 'ramses_starter'
    summary = 'Ramses starter'

    def pre(self, command, output_dir, vars):
        dbengine_choices = {'1': 'sqla', '2': 'mongodb'}
        vars['engine'] = dbengine_choices[moves.input("""
        Which database backend would you like to use:

        (1) for SQLAlchemy/PostgreSQL, or
        (2) for MongoEngine/MongoDB?

        [default is '1']: """) or '1']

        if vars['package'] == 'site':
            raise ValueError("""
                "Site" is a reserved keyword in Python.
                 Please use a different project name. """)

    def post(self, command, output_dir, vars):
        os.chdir(str(output_dir))
        subprocess.call('pip install -r requirements.txt', shell=True)
        subprocess.call('pip install nefertari-{}'.format(vars['engine']),
                        shell=True)
        msg = """Goodbye boilerplate! Welcome to Ramses."""
        self.out(msg)
