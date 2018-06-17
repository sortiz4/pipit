import alpha
import argparse
import json
import os
import re
import sys
from functools import reduce
from subprocess import PIPE
from subprocess import run

ANY = '*'
DEP = 'dependencies'
DEV = 'dev-' + DEP
PLATFORM = 'platform'
PYTHON = 'python'
VERSION = 'version'


def isupdatable(info):
    """
    Determines if a package is updatable (non-external).
    """
    try:
        if isinstance(info, dict):
            version = info.get(VERSION, ANY)
        else:
            version = info
        return not version[0].isalpha()
    except IndexError:
        return False


class cachedproperty:
    """
    Converts a method into a lazy property.
    """

    def __init__(self, method):
        self.__doc__ = method.__doc__
        self.__name__ = method.__name__
        self.method = method

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        result = instance.__dict__[self.__name__] = self.method(instance)
        return result


class Pip:
    """
    A collection of methods that map to various pip tasks.
    """
    env = '.pipenv'
    file = 'pip.json'

    @classmethod
    def create(cls):
        """
        Creates the dependency file (if it doesn't exist).
        """
        if not os.path.exists(cls.file):
            with open(cls.file, 'w') as file:
                json.dump({}, file)
                print('', file=file)

    @classmethod
    def read(cls):
        """
        Loads the dependency file.
        """
        with open(cls.file) as file:
            pip = json.load(file)
        for field in [DEP, DEV]:
            try:
                schema = pip[field]
            except KeyError:
                continue
            # Normalize the package names
            pip[field] = {k.lower(): v for k, v in schema.items()}
        return pip

    @classmethod
    def write(cls, pip):
        """
        Updates the dependency file.
        """
        for field in [DEP, DEV]:
            # Remove empty fields
            try:
                if len(pip[field]) == 0:
                    del pip[field]
            except KeyError:
                continue
        with open(cls.file, 'w') as file:
            json.dump(pip, file, indent=2, sort_keys=True)
            print('', file=file)

    @classmethod
    def run(cls, *args, **kwargs):
        """
        Executes the local pip command.
        """
        bin = 'Scripts' if os.name == 'nt' else 'bin'
        pip = os.path.abspath(os.path.join(cls.env, bin, 'pip'))
        return run([pip, *args], **kwargs)

    @classmethod
    def install(cls, *args):
        """
        Installs the given packages.
        """
        return cls.run('install', *args)

    @classmethod
    def uninstall(cls, *args):
        """
        Uninstalls the given packages.
        """
        return cls.run('uninstall', '-y', *args)

    @classmethod
    def update(cls, *args):
        """
        Updates the given packages.
        """
        flags = ['-U' for _ in range(len(args))]
        return cls.install(*[_ for _ in zip(flags, args) for _ in _])

    @classmethod
    def list(cls, *args, **kwargs):
        """
        Lists the installed packages.
        """
        return cls.run('list', *args, **kwargs)

    @classmethod
    def installed(cls, *args):
        """
        Lists the installed packages in JSON.
        """
        process = cls.list('--format=json', *args, shell=True, stdout=PIPE)
        installed = json.loads(process.stdout.decode(sys.stdout.encoding))
        return {pkg['name'].lower(): pkg['version'] for pkg in installed}

    @classmethod
    def outdated(cls):
        """
        Lists the outdated packages in JSON.
        """
        return cls.installed('-o')


class Command:
    """
    The actual command including the parser.
    """

    def __init__(self, *args):
        """
        Initializes and parses the arguments.
        """
        parser = argparse.ArgumentParser(
            description='Yet another Python dependency manager.',
        )
        parser.add_argument(
            '-v',
            '--version',
            action='version',
            version='%(prog)s 1.0',
            help="Show this program's version and exit.",
        )
        parser.set_defaults(func=lambda: None)
        subparsers = parser.add_subparsers()

        # Defines the `new` command
        new = subparsers.add_parser(
            'new',
            description='Create a new virtual environment.',
        )
        new.add_argument(
            'path',
            nargs='?',
            help='Where to install the environment.',
        )
        new.set_defaults(func=self.new)

        # Defines the `install` command
        install = subparsers.add_parser(
            'install',
            description='Install packages and dependencies.',
        )
        install.add_argument(
            'packages',
            nargs='*',
            help='A list of packages to install.',
        )
        install.add_argument(
            '-d',
            '--dev',
            action='store_true',
            help='Install development packages or dependencies.',
        )
        install.set_defaults(func=self.install)

        # Defines the `uninstall` command
        uninstall = subparsers.add_parser(
            'uninstall',
            description='Uninstall packages and dependencies.',
        )
        uninstall.add_argument(
            'packages',
            nargs='+',
            help='A list of packages to uninstall.',
        )
        uninstall.set_defaults(func=self.uninstall)

        # Defines the `update` command
        update = subparsers.add_parser(
            'update',
            description='Update installed PyPI dependencies.',
        )
        update.add_argument(
            'packages',
            nargs='*',
            help='A list of packages to update.',
        )
        update.set_defaults(func=self.update)

        # Defines the `list` command
        list = subparsers.add_parser(
            'list',
            description='List installed packages.',
        )
        list.add_argument(
            '-o',
            '--outdated',
            action='store_true',
            help='Only list outdated packages.',
        )
        list.set_defaults(func=self.list)

        # Parse the arguments
        self.args = parser.parse_args(args or None)

    @cachedproperty
    def packages(self):
        """
        Captures and normalizes package names and versions.
        """
        packages = []
        pattern_pip = re.compile('([\w-]+)(.*)')
        pattern_vcs = re.compile('(.+)#egg=([\w-]+)')
        for package in self.args.packages:
            match = pattern_vcs.fullmatch(package)
            if match:
                # The package is a URL
                name = match.group(2).lower()
                version = match.group(1)
            else:
                # The package belongs to PyPI
                match = pattern_pip.fullmatch(package)
                name = match.group(1).lower()
                version = match.group(2).strip('=')
            packages.append((name, version))
        return packages

    def handle(self):
        """
        Calls the appropriate command method.
        """
        self.args.func()

    def new(self):
        """
        Creates a new virtual environment.
        """
        path = os.path.join(self.args.path or '', Pip.env)
        if not os.path.exists(path):
            run(['virtualenv', path])
        Pip.create()

    def install(self):
        """
        Installs packages and dependencies.
        """
        try:
            pip = Pip.read()
        except FileNotFoundError:
            return

        if self.args.packages:
            # Install the packages
            Pip.install(*self.args.packages)
            installed = Pip.installed()

            # Add the field if it doesn't exist
            field = DEP if not self.args.dev else DEV
            if field not in pip:
                schema = pip[field] = {}
            else:
                schema = pip[field]

            # Update the dependencies
            for name, version in self.packages:
                if not version:
                    # Retrieve the installed version
                    version = '~=' + installed[name]
                try:
                    schema[name][VERSION] = version
                except (KeyError, TypeError):
                    schema[name] = version

            # Update the dependency file
            Pip.write(pip)
        else:
            # No packages provided (install dependencies)
            fields = [DEP]
            if self.args.dev:
                fields.append(DEV)

            # Collect the appropriate packages
            packages = []
            for field in fields:
                try:
                    schema = pip[field]
                except KeyError:
                    continue
                for name, info in schema.items():
                    if isinstance(info, dict):
                        # Check the platform
                        try:
                            platform = info[PLATFORM]
                            if os.name not in platform.split(','):
                                # Skip this package if it's
                                # not meant for this platform
                                continue
                        except KeyError:
                            pass

                        # Check the Python version
                        try:
                            python = info[PYTHON]
                            if not reduce(
                                lambda a, b: a or sys.version.startswith(b),
                                python.split(','),
                                False,
                            ):
                                # Skip this package if it's
                                # not meant for this Python
                                continue
                        except KeyError:
                            pass

                        # Get the version string
                        version = info.get(VERSION, ANY)
                    else:
                        version = info

                    # Format the install string (version must not be empty)
                    if version == ANY:
                        packages.append(name)
                    elif version[0].isdigit():
                        packages.append('{}=={}'.format(name, version))
                    elif version[0].isalpha():
                        packages.append('{}#egg={}'.format(version, name))
                    else:
                        packages.append('{}{}'.format(name, version))

            # Install the collected packages
            if len(packages) > 0:
                Pip.install(*packages)

    def uninstall(self):
        """
        Uninstalls packages and dependencies.
        """
        try:
            pip = Pip.read()
        except FileNotFoundError:
            return

        # Uninstall the packages
        Pip.uninstall(*self.args.packages)

        # Remove the dependencies
        for field in [DEP, DEV]:
            try:
                schema = pip[field]
            except KeyError:
                continue
            for package, _ in self.packages:
                try:
                    del schema[package]
                except KeyError:
                    continue

        # Update the dependency file
        Pip.write(pip)

    def update(self):
        """
        Updates installed PyPI dependencies.
        """
        try:
            pip = Pip.read()
        except FileNotFoundError:
            return

        # Compute the minimum updatable set (exclude external packages)
        dependencies = {*{
                name for name, info
                in pip.get(DEP, {}).items()
                if isupdatable(info)
            }, *{
                name for name, info
                in pip.get(DEV, {}).items()
                if isupdatable(info)
        }}
        outdated = Pip.outdated()

        if self.args.packages:
            # Intersect arguments, dependencies, and outdated packages
            updatable = [
                pkg for pkg in [pkg for pkg, _ in self.packages]
                if pkg in dependencies and pkg in outdated
            ]
        else:
            # Intersect dependencies and outdated packages
            updatable = [pkg for pkg in dependencies if pkg in outdated]

        # Update the updatable packages
        if len(updatable) > 0:
            Pip.update(*updatable)
            installed = Pip.installed()

            # Get the updated package version
            updated = [(name, '~=' + installed[name]) for name in updatable]

            # Update the dependencies
            for field in [DEP, DEV]:
                try:
                    schema = pip[field]
                except KeyError:
                    continue
                for name, version in updated:
                    if name in schema:
                        try:
                            schema[name][VERSION] = version
                        except TypeError:
                            schema[name] = version

            # Update the dependency file
            Pip.write(pip)

    def list(self):
        """
        Lists installed packages.
        """
        Pip.list('-o' if self.args.outdated else '')


if __name__ == '__main__':
    Command().handle()
