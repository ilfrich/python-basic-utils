# Python Basic Utilities `pbu`

## Installation

Simply run:

```bash
make local-install
```

> _It may ask you for your root password, as packages need to be installed as root_

> _The Makefile assumes you run pip via the `pip3` command_

## Usage

If you have a requirement.txt file, you can add `python-basic-utils`:

```bash
python-basic-utils==0.1.0
```

Then, simply import the class / module you need:

```python
from pbu.data import JSON

# and start using it
obj = JSON({"my": {"obj": "content"}})
print(obj.my.obj)
```

## Classes

### JSON

This is an adaptation of the native `dict` class, providing Javascript-like dictionary access using the "dot-notation" 
(e.g. `person.relations[0].address.street`) rather than the Python-native bracket notation (e.g. 
`person["relations"][0]["address"]["street"]`). It overrides the basic `__getattr__` and `__setattr__` methods to as a 
shortcut to manage the dictionary content.

**Example**

```python
from pbu.data import JSON
my_obj = JSON({"initial": "content"})
print(my_obj.initial)
# prints out "content"

my_obj.initial = {"a": 5, "b": 3}
print(my_obj.initial.a + my_obj.initial.b)
# prints out 8
my_obj.initial.b = 13
print(my_obj.initial.a + my_obj.initial.b)
# prints out 18

my_obj.extension = 10
print(my_obj.extension)
# prints out 10
```
