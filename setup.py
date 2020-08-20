from setuptools import setup, find_packages
import os

INSTALL_REQUIRES = []
INSTALL_REQUIRES.append('graphviz')
INSTALL_REQUIRES.append('pyyaml')

license='MIT'
if os.path.exists('LICENSE.txt'):
  license = open('LICENSE.txt').read()

long_description = """
    The Python package and command line utility for transforming .mpl, .lp, .mps data files to .mps, .lp, .xa, .mpl, mod and others.
    https://github.com/pashtetgp/opt_convert - README
  """

setup(name='sndp_gen',
      version='0.0.1',
      python_requires='>=3.6', # does not work for some reason
      description='Converter for mathematical optimization formats: .mpl, .lp, .mps -> .mps, .lp, .xa, .mpl, mod etc.',
      long_description=long_description,
      keywords='converter mathematical optimization mps',
      author='Pavlo Glushko',
      author_email='pavloglushko@gmail.com',
      url='https://github.com/pashtetgp/opt_convert',
      download_url='https://github.com/pashtetgp/opt_convert/tarball/0.0.1',
      license=license,
      packages=find_packages(),      classifiers=[
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering :: Mathematics',
        ],
      include_package_data=True, # files from MANIFEST.in
      test_suite='tests',
      entry_points = {
        'console_scripts': ['sndp_gen=sndp_gen.command_line:command_line'],
      },
      install_requires=INSTALL_REQUIRES
)