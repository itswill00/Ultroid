from .. import udB


class KeyManager:
    def __init__(self, key, cast=None) -> None:
        self._key = key
        self._cast = cast

    def get(self):
        _data = udB.get_key(self._key)
        if _data is None:
            return self._cast() if callable(self._cast) else self._cast
        if self._cast and not isinstance(_data, self._cast):
            return [_data] if self._cast == list else self._cast(_data)
        return _data

    def get_child(self, key):
        return self.get()[key]

    def count(self):
        return len(self.get())

    def add(self, item):
        content = self.get()
        if content is None:
            content = type(item)()
            
        if isinstance(content, dict) and isinstance(item, dict):
            content.update(item)
        elif isinstance(content, list) and item not in content:
            content.append(item)
        else:
            return
        udB.set_key(self._key, content)

    def remove(self, item):
        content = self.get()
        if not content:
             return
             
        if isinstance(content, list) and item in content:
            content.remove(item)
        elif isinstance(content, dict) and item in content:
            del content[item]
        else:
            return
        udB.set_key(self._key, content)

    def contains(self, item):
        return item in self.get()
