from setuptools import setup
  
setup(
    name='DMFsim-benchmarking',
    version='1.0',
    description='Source independent DMFsim benchmarking',
    author='Peyton Okubo',
    author_email='okubo012@umn.edu',
    packages=['DMFsim-benchmarking'],
    install_requires=[
        'numpy',
        'pandas',
        'matplotlib',
    ],
)
