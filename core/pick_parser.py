class PickParser(object):

    __slots__= (
        "spec_version"
    )

    def __init__(
            self,
            spec_version,
    ):
        self.spec_version = spec_version
        self()