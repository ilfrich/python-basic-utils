from setuptools import setup

setup(name="pbu",
      version="0.3.8",
      description="Basic Utility module for the Python programming language",
      url="https://github.com/ilfrich/python-basic-utils",
      author="Peter Ilfrich",
      author_email="das-peter@gmx.de",
      license="Apache-2.0",
      packages=[
          "pbu"
      ],
      install_requires=[
            "mysql-connector-python",
            "pytz",
            "bson",
            "pymongo",
            "tzlocal",
      ],
      tests_require=[
          "pytest",
      ],
      zip_safe=False)
