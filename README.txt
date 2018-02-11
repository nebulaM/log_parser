Log parser

Dependency:
Python 2.7.10 https://www.python.org/downloads/release/python-2710/ or above

Usage:

Translate MSGU register dump:

python main.py msgu -i path/to/input/dump_file [-w path/to/basecode/workspace] [-o path/to/output_dir] [-d]

If [-w path/to/basecode/workspace] is defined, then for MSGU Firmware log, use header file from the given workspace

Translate OSSP register dump:

python main.py ossp -i path/to/input/dump_file [-o path/to/output_dir] [-d]

include/doc folder(contains def file) is missing from this repo so the parser cannot work properly. 