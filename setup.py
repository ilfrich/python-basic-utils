from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name="pbu",
      version="0.6.2",
      description="Basic Utility module for the Python programming language",
      long_description=long_description,
      long_description_content_type="text/markdown",
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
            "requests",
      ],
      tests_require=[
          "pytest",
      ],
      zip_safe=False)
