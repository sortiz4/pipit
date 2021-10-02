from . import __patch__
import argparse
import json
import os
import re
import sys
from functools import reduce
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import run


class Clauses:
    """
    Version specifier clauses.
    """
    ANY = '*'
    COM = '~='


class Schema:
    """
    Dependency file schema.
    """
    DEPS = 'dependencies'
    DEVD = 'dev-' + DEPS
    FIELDS = [DEPS, DEVD]
    PYTHON = 'python'
    SYSTEM = 'system'
    VERSION = 'version'


def isupdatable(info):
    """
    Determines if a package is updatable (non-external).
    """
    try:
        if isinstance(info, dict):
            version = info.get(Schema.VERSION, Clauses.ANY)
        else:
            version = info
        return isinstance(version, str) and not version[0].isalpha()
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
    env = '.pipit'
    file = 'pipit.json'

    @classmethod
    def create(cls, base):
        """
        Creates the dependency file (if it doesn't exist).
        """
        path = os.path.join(base, cls.file)
        if not os.path.exists(path):
            with open(path, 'w') as file:
                json.dump({}, file)
                print('', file=file)

    @classmethod
    def read(cls):
        """
        Loads the dependency file.
        """
        with open(cls.file) as file:
            pip = json.load(file)
        for field in Schema.FIELDS:
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
        for field in Schema.FIELDS:
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
        return run([pip, *args], **kwargs, check=True)

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
    name = 'pipit'
    version = '0.4.0'

    def __init__(self, *args):
        """
        Initializes and parses the arguments.
        """
        parser = argparse.ArgumentParser(
            usage='%(prog)s [options] [command]',
            description='Yet another Python dependency manager.',
        )
        parser.add_argument(
            '-v',
            '--version',
            action='version',
            version='%(prog)s ' + self.version,
            help="Show this program's version and exit.",
        )
        parser.set_defaults(func=lambda: None)
        subparsers = parser.add_subparsers(prog=self.name)

        # Defines the `new` command
        new = subparsers.add_parser(
            'new',
            usage='%(prog)s [options] [path]',
            description='Create a new virtual environment.',
        )
        new.add_argument(
            'path',
            nargs='?',
            help='Where to install the environment.',
        )
        new.add_argument(
            '-p',
            '--python',
            type=str,
            help='The Python interpreter to use.',
        )
        new.set_defaults(func=self.new)

        # Defines the `install` command
        install = subparsers.add_parser(
            'install',
            usage='%(prog)s [options] [packages]',
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
            usage='%(prog)s [options] packages',
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
            usage='%(prog)s [options] [packages]',
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
            usage='%(prog)s [options]',
            description='List installed packages.',
        )
        list.set_defaults(func=self.list)

        # Defines the `outdated` command
        outdated = subparsers.add_parser(
            'outdated',
            usage='%(prog)s [options]',
            description='List outdated packages.',
        )
        outdated.set_defaults(func=self.outdated)

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
        base = self.args.path or ''
        path = os.path.join(base, Pip.env)
        args = ['virtualenv', path]

        if self.args.python:
            # Append the given Python interpreter
            args.append('-p ' + self.args.python)

        # Create the environment if it does not exist
        if not os.path.exists(path):
            run(args, check=True)
        Pip.create(base)

    def install(self):
        """
        Installs packages and dependencies.
        """
        # Try to create an environment before installing anything
        self.args.path = None
        self.args.python = None
        self.new()
        pip = Pip.read()

        if self.args.packages:
            # Install the packages
            Pip.install(*self.args.packages)
            installed = Pip.installed()

            # Add the field if it doesn't exist
            field = Schema.DEPS if not self.args.dev else Schema.DEVD
            if field not in pip:
                schema = pip[field] = {}
            else:
                schema = pip[field]

            # Update the dependencies
            for name, version in self.packages:
                if not version:
                    # Retrieve the installed version
                    version = Clauses.COM + installed[name]
                try:
                    schema[name][Schema.VERSION] = version
                except (KeyError, TypeError):
                    schema[name] = version

            # Update the dependency file
            Pip.write(pip)
        else:
            # No packages provided (install dependencies)
            fields = [Schema.DEPS]
            if self.args.dev:
                fields.append(Schema.DEVD)

            # Collect the appropriate packages
            packages = []
            for field in fields:
                try:
                    schema = pip[field]
                except KeyError:
                    continue
                for name, info in schema.items():
                    if isinstance(info, dict):
                        # Check the Python version
                        try:
                            python = info[Schema.PYTHON]
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

                        # Check the system string
                        try:
                            system = info[Schema.SYSTEM]
                            if os.name not in system.split(','):
                                # Skip this package if it's
                                # not meant for this system
                                continue
                        except KeyError:
                            pass

                        # Get the version string
                        version = info.get(Schema.VERSION, Clauses.ANY)
                    else:
                        version = info

                    # Format the install string (version must not be empty)
                    if version == Clauses.ANY:
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
        pip = Pip.read()

        # Uninstall the packages
        Pip.uninstall(*self.args.packages)

        # Remove the dependencies
        for field in Schema.FIELDS:
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
        pip = Pip.read()

        # Compute the minimum updatable set (exclude external packages)
        dependencies = {
            *{
                name for name, info in pip.get(Schema.DEPS, {}).items()
                if isupdatable(info)
            },
            *{
                name for name, info in pip.get(Schema.DEVD, {}).items()
                if isupdatable(info)
            },
        }
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
            updated = [
                (name, Clauses.COM + installed[name]) for name in updatable
            ]

            # Update the dependencies
            for field in Schema.FIELDS:
                try:
                    schema = pip[field]
                except KeyError:
                    continue
                for name, version in updated:
                    if name in schema:
                        try:
                            schema[name][Schema.VERSION] = version
                        except TypeError:
                            schema[name] = version

            # Update the dependency file
            Pip.write(pip)

    def list(self):
        """
        Lists installed packages.
        """
        Pip.list()

    def outdated(self):
        """
        Lists outdated packages.
        """
        Pip.list('-o')


def error(*args, **kwargs):
    """
    Formatted error messaging.
    """
    print(Command.name + ': error:', *args, **kwargs, file=sys.stderr)


def main():
    """
    Execute the command and gracefully handle all errors.
    """
    try:
        Command().handle()
    except CalledProcessError:
        pass
    except (AttributeError, IndexError, TypeError, ValueError):
        error('malformed dependency file or package arguments')
    except FileNotFoundError:
        error('the dependency file could not be found')
    except OSError:
        error('an operating system error occurred')
    except Exception:
        error('an unknown error occurred')
