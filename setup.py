# -*- coding: utf-8 -*-
from setuptools import setup


setup(
    name='smart_exporter',
    version='0.0.1',
    packages=['smart_exporter'],
    entry_points={
        'console_scripts': ['smart_exporter=smart_exporter.smart_exporter:main'],
    },
)
