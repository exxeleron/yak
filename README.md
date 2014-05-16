## yak 3.0

yak is an application used to manage Enterprise Components deployed on a single host.

It is capable of starting, stopping, restarting different processes and collecting information using convenient command line interface.

### Building package

#### Branding application

The yak script can be branded with current version, timestamp by altering the code before creating the package. 

To brand using values defined in `setup.py` execute: `python setup.py imprint`.

Version and timestamp values can be ovverriden from command line: `python setup.py imprint --version=3.0.0 --tstamp=20140415114830`.


#### Freezing application

Executable version of the yak is created with the [bbfreeze](https://pypi.python.org/pypi/bbfreeze) tool.

Requirements:
 - bbfreeze package installed

Instructions:
 - Execute:
   `python setup.py freeze`
 - Binary distribution is being built to directory:
   `dist/yak-${platform}`


#### Testing

Application uses py.test as a test runner for unit tests.

Instructions:
 - Make sure that top directory is included in the `PYTHONPATH`
 - Execute: `py.test`


#### Requirements

 - Python 2.7 (Python 2.6 can be used if ordereddict package is installed)
 - altgraph 0.9
 - bbfreeze 1.1.2
 - bbfreeze-loader 1.1.2
 - configobj 5.0.4
 - psutil 1.2.1
 - pywin32 (required on: windows) 
 - pyreadline 1.7 (required on: windows)


Required libraries can be installed using [pip](https://pypi.python.org/pypi/pip).
Execute: `pip install -r requirements.txt`

Note that this does not install additional Windows dependencies.
