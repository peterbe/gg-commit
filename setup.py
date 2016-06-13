from os import path
from setuptools import setup, find_packages

_here = path.dirname(__file__)


setup(
    name='gg-commit',
    version='0.0.1',
    description='Plugin for gg for committing branches',
    long_description=open(path.join(_here, 'README.rst')).read(),
    py_modules=['gg_commit'],
    author='Peter Bengtsson',
    author_email='mail@peterbe.com',
    url='https://github.com/peterbe/gg-commit',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['gg'],
    entry_points="""
        [gg.plugin]
        cli=gg_commit:commit
    """,
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock', 'pytest-mock'],
)
