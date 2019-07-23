from setuptools import setup

setup(name="python-basic-utils",
      version="0.2.2",
      description="Basic Utility module for the Python programming language",
      url="https://github.ibm.com/aur-pro/python-basic-utils",
      author="Peter Ilfrich",
      author_email="peter.ilfrich@au1.ibm.com",
      license="Copyright IBM Corporation 2019",
      packages=[
          "pbu"
      ],
      install_requires=[
            "mysql-connector-python",
            "pytz",
            "bson",
            "pymongo"
      ],
      tests_require=[
          "pytest",
      ],
      zip_safe=False)
