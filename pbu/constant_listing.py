import inspect


class ConstantListing:
    def get_all(self):
        """ Returns list of strings of the attributes of the provided class """
        provided_class = self.__class__
        attributes = inspect.getmembers(provided_class, lambda a: not (inspect.isroutine(a)))
        return [a[0] for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))]

    def get_all_values(self):
        return list(map(lambda x: getattr(self, x), self.get_all()))
