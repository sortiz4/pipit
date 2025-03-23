# Pipit
`pipit` is a lightweight Python dependency manager and a thin layer built on
top of `pip`. Designed with simplicity in mind, `pipit` provides just enough
abstraction to make package management more convenient and efficient for
developers. This is an old tool and shouldn't be used.

## Installation
`pipit` requires Python 3, `virtualenv`, and `pip`. Once these requirements
have been met, `pipit` can be installed through `pip` directly from GitHub.

```sh
$ pip install git+https://github.com/sortiz4/pipit.git#egg=pipit
```

## Usage
A brief overview of the commands and their behaviors are described below. Note
that while the `packages` provided through the command-line will be passed to
`pip` (and therefore must be compatible), only PyPI packages (with optional
version clauses) and version control URLs (*with* the egg and *without*
the subdirectory specifier) are supported by this tool.

An example is provided:

```sh
$ pipit install certifi 'django>=2.*' 'pytz==2018.*' git+https://github.com/urllib3/urllib3.git#egg=urllib3
```

### new
```sh
$ pipit new [path]
```

`new` will create a fresh virtual environment, `.pipit`, and a dependency file,
`pipit.json`, in the current directory or the directory provided by the
optional `path` argument.

### install
```sh
$ pipit install [-d] [packages]
```

`install` has two different modes of operation: with or without `packages`.

1. If `packages` are provided, the tool will install the packages and add them
   to your `dependencies` using the latest compatible version. If the `--dev`
   option is provided, they will be added to your `dev-dependencies`.
2. If no `packages` are provided, the tool will install your `dependencies`,
   respecting both `python` and `system` constraints. If the `--dev` option is
   provided, the tool will install your `dev-dependencies`.

### uninstall
```sh
$ pipit uninstall packages
```

`uninstall` will uninstall the `packages` and remove them from `dependencies`
and `dev-dependencies`. The tool will not uninstall dangling packages.

### update
```sh
$ pipit update [packages]
```

`update` has two different modes of operation: with or without `packages`. Note
that version controlled dependencies must be updated manually using `install`.

1. If `packages` are provided, the tool will only update the given packages
   *installed* as `dependencies` or `dev-dependencies`.
2. If no `packages` are provided, the tool will update all of the *installed*
   `dependencies` and `dev-dependencies`.

### list
```sh
$ pipit list [-o]
```

`list` displays all of the installed packages. If the `--outdated` option is
provided, only the outdated installed packages will be shown.

## Schema
`pipit.json` describes your project dependencies as a JSON object with two
optional fields: `dependencies` and `dev-dependencies`. Both fields must be
JSON objects with each field mapping a package name to its version information.

Version information may be a string or an object. A version object may contain
three optional fields: `python`, `system`, and `version`.

1. `python` is a comma-separated string of exclusive Python versions where the
   package may be installed. If `python` is not provided, then the package will
   be installed on all Python versions.
2. `system` is a comma-separated string of exclusive systems where the package
   may be installed (defined by `os.name`). If `system` is not provided, then
   the package will be installed on all systems.
3. `version` is a string representing the package version to install. If
   `version` is not provided, any version will be assumed.

Version strings must either be a version specifier (PEP 440) or one of the
supported version control URL schemes supported by `pip`.

1. If the version string is a version specifier, the tool will assume the
   package is available on PyPI. There are a few changes to keep in mind:
   1. Version matching clauses (`==`) may be omitted.
   2. Arbitrary equality clauses (`===`) are not supported.
   3. Wildcards (`*`) represent any version.
2. If the version string is a version control URL, it should match the
   following pattern: `{VCS}+{URL}[@{ID}]`.

### Example
```json
{
  "dependencies": {
    "certifi": "*",
    "django": ">=2.0,<=2.1",
    "gunicorn": {
      "system": "posix",
      "version": "19.8.*"
    },
    "pytz": "~=2018.3"
  },
  "dev-dependencies": {
    "pytest": {
      "python": "3.5,3.6",
      "version": "git+https://github.com/pytest-dev/pytest.git"
    },
    "selenium": {
      "system": "nt"
    },
    "urllib3": "git+https://github.com/urllib3/urllib3.git"
  }
}
```
