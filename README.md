# ska_helpers

This is a collection of utilities for ACA packages.
It currently includes:

- get_version. A function to get the version from installed package information ot git.

    from ska_helpers import get_version
    version = get_version('chandra_aca')
    
    import ska_helpers.version
    print(ska_helpers.version.parse_version(version))
