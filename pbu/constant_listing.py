import inspect
from typing import Any, List, Optional


class ConstantListing:
    def get_all(self):
        """ Returns list of strings of the attributes of the provided class """
        provided_class = self.__class__
        attributes = inspect.getmembers(provided_class, lambda a: not (inspect.isroutine(a)))
        return [a[0] for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))]

    def get_all_values(self) -> List[Any]:
        return list(map(lambda x: getattr(self, x), self.get_all()))

    def get(self, key: str) -> Optional[Any]:
        if key not in self.get_all():
            return None
        return getattr(self, key)

    def reverse_lookup(self, value: Any) -> Optional[str]:
        if value not in self.get_all_values():
            return None
        
        keys = self.get_all()
        for key in keys:
            if getattr(self, key) == value:
                return key
            
        return None  # should not get here
