## yak 3.1

yak is an application used to manage Enterprise Components deployed on a single host.

It is capable of starting, stopping, restarting different processes and collecting information using convenient command line interface.


### Documentation

 - [Usage](doc/Usage.md)
 - [Configuration](doc/Configuration.md)


### OS support

Primary operating system for yak is Linux. yak also provides limited/experimental support for Windows and Mac OS X.

#### Windows

Limitations:
 - `interrupt` command terminates process instead of sending an interruption signal

#### Mac OS X (experimental)

Limitations:
 - `cpuAffinity` configuration attribute is not supported and is ignored


### Building package

#### Branding application

The yak script can be branded with current version, timestamp by altering the code before creating the package. 

To brand using values defined in `setup.py` execute:

`python setup.py imprint`.

Version and timestamp values can be ovverriden from command line: 

`python setup.py imprint --version=3.0.0 --tstamp=20140415114830`.


#### Freezing application

Executable version of the yak is created with the [pyinstaller](http://www.pyinstaller.org/) tool.

Requirements:
 - pyinstaller package installed

Instructions:

Execute:

  `pyinstaller yak.spec`
  
or:

  `pyinstaller yak-win.spec` on Windows platform

Binary distribution is being built to directory: `dist/yak`.


#### Packaging application

Binary distribution can be packed to a single ZIP archive by executing:

`python setup.py package`

   
#### Testing

Application uses py.test as a test runner for unit tests.

Instructions:
 - Make sure that top directory is included in the `PYTHONPATH`
 - Execute: `py.test`


#### Requirements

 - Python 2.7 (Python 2.6 can be used if ordereddict package is installed)
 - pyinstaller 2.1
 - configobj 5.0.4
 - psutil 1.2.1
 - pywin32 (required on: windows) 
 - pyreadline 1.7 (required on: windows)

Required libraries can be conveniently installed using [pip](https://pypi.python.org/pypi/pip).
Execute: 

`pip install -r requirements.txt` to install dependencies.

Note that this does not install additional Windows dependencies.
