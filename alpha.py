import gettext

# Hash map of the replacement strings
MAP = {
    'optional arguments': 'Optional arguments',
    'positional arguments': 'Positional arguments',
    'show this help message and exit': 'Show this help message and exit.',
    'usage: ': 'Usage: ',
}


# Monkey patch the translation function
def replace(message):
    try:
        return MAP[message]
    except KeyError:
        return message


gettext.gettext = replace
