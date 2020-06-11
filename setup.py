from setuptools import setup

setup(
    name='HadFFR',
    packages=['bparking_common'],
    include_package_data=True,
    install_requires=['coffea', 'xxhash', 'scipy', 'mplhep', 'cloudpickle', 'numexpr'],
)
