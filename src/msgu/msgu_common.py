import sys
import os
import re
import argparse
from ..shared import dutil as ut

class MSGULog(object):
    MODULE = 'msgu'
    SECTION = 'common'
    # input crash dump dir, this will be set from to cmd line input
    INPUT_DIR = ''
    # output dir that saves result. If not given by cmd line input, default is the one below
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'result')
    # include dir that contains some definition files for some of the parsers
    INCLUDE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'include')
    # enable debugging if set to true through cmd line input
    DEBUG_MODE = False
    # common MSGU address offset to CPU address
    MSGU_ADDRESS_OFFSET = 0xbf400000
    
    ENDIANNESS = 'little'
    
    # chipset name
    LUXOR = 'Luxor'
    WF = 'WILDFIRE'

    # how many chars per line in crash dump msgu section
    LOG_LINE_LENGTH = 82

    # how many byte per register value displayed on crash dump
    BYTE_PER_VAL = 4
    # how many register value per register address is dumped on a line
    VAL_PER_LINE = 8

    # min and max number of argument for set_input_params_classic()
    MIN_ARGC = 1
    MAX_ARGC = 3

    # default chipset, this will be overwritten by calling set_chipset()
    chipset = LUXOR
    # regular expression for things like 'When set to logic'
    re_logic = re.compile('When([a-zA-Z\s]+)logic:')
    # regular expression token that replace contents with hex in definition files
    re_hex_token = re.compile('@PARSE_REPLACE_VALUE_HEX_START@[a-zA-Z0-9\s_]+@PARSE_REPLACE_VALUE_HEX_END@')
    # regular expression token that replace contents with decimal in definition files 
    re_dec_token = re.compile('@PARSE_REPLACE_VALUE_START@[a-zA-Z0-9\s_]+@PARSE_REPLACE_VALUE_END@')

    @classmethod
    def input_params_classic_help(cls, script_name):
        print 'Usage:\n'
        print '  python [' + script_name + '] [path\\to\\input\\filename.txt] [path\\to\\output_dir] [debug]\n'
        print '  If [path/to/output_dir] is not given, then result will be saved in [result] folder\n'
        print '  If [debug] is given, then print out additional log\n'

    @classmethod
    def set_input_params(cls):
        flag_use_standard = False
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            flag_use_standard = True
        else:
            for argv in sys.argv:
                if argv == '-i' or argv == '--input':
                    flag_use_standard = True
                    break
        if flag_use_standard is True:
            cls.set_input_params_standard()
        else:
            cls.set_input_params_classic()
        cls.common_out_filename = ut.get_parsed_filename(cls.INPUT_DIR, cls.MODULE, None) + '.html'
        cls.common_out_filename = os.path.join(cls.OUTPUT_DIR, cls.common_out_filename)

    @classmethod
    def set_input_params_standard(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input", help="path to input crash dump", required=True)
        parser.add_argument("-o", "--out", help="path to output folder for result", default=cls.OUTPUT_DIR)
        parser.add_argument("-d", "--debug", help="set to true to enable additional log", default=False)
        args = parser.parse_args()
        if os.path.isfile(args.input):
            cls.INPUT_DIR = args.input
            cls.OUTPUT_DIR = args.out
            cls.DEBUG_MODE = args.debug
        else:
            parser.print_help()
            sys.exit(1)
    
    @classmethod
    def set_input_params_classic(cls):
        # +1 because python count 'python' as an argument
        if len(sys.argv) < (cls.MIN_ARGC + 1) or len(sys.argv) > (cls.MAX_ARGC + 1):
            print ('\nExpect %d-%d argument(s), but have %d argument(s)\n') % (cls.MIN_ARGC, cls.MAX_ARGC, len(sys.argv))
            cls.input_params_classic_help(sys.argv[0])
            sys.exit(1)

        if sys.argv[1] == '-help' or sys.argv[1] == '--h' or sys.argv[1] == 'HELP' or sys.argv[1] == 'help':
            cls.input_params_classic_help(sys.argv[0])
            sys.exit(1)
        # first(1+1, remember +1 because python count 'python' as an argument)
        # argv is input dir
        if os.path.isfile(sys.argv[1]):
            cls.INPUT_DIR = sys.argv[1]
        else:
            cls.input_params_classic_help(sys.argv[0])
            sys.exit(1)
        # when 2 arguments are given: 1st argv is input dir, 2nd argv is debug or output dir
        if len(sys.argv) == cls.MAX_ARGC:
            # second(2+1, remember +1 because python count 'python' as an argument) 
            # argv is debug
            if sys.argv[2] == 'debug' or sys.argv[2] == '-d':
                cls.DEBUG_MODE = True
            else:
                cls.OUTPUT_DIR = sys.argv[2]
        elif len(sys.argv) == (cls.MAX_ARGC + 1):
            cls.INPUT_DIR = sys.argv[1]
            cls.OUTPUT_DIR = sys.argv[2]
            if sys.argv[3] == 'debug' or sys.argv[3] == '-d':
                cls.DEBUG_MODE = True

    @classmethod
    def set_chipset(cls):
        if cls.INPUT_DIR is '':
            raise ValueError('Input dir not defined.')
        flag_found = False
        lines = ut.get_data_from_file(None, cls.INPUT_DIR)
        for line in lines:
            if 'ASIC Family' in line:
                if cls.LUXOR in line:
                    cls.chipset = cls.LUXOR
                    flag_found = True
                elif cls.WF in line:
                    cls.chipset = cls.WF
                    flag_found = True
                break
        if flag_found is True:
            print "From the input file, chipset is " + cls.chipset
        else:
            print "Cannot read chipset from the input file, use default chipset " + cls.chipset
    
    @classmethod
    def get_reg_val_list(cls, tag, header, ending, byte_per_reg):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'get_reg_val_list')
        crash_dump_reg_list = []
        lines = ut.save_line_to_list(tag_next_level, header, ending, \
        cls.INPUT_DIR, cls.LOG_LINE_LENGTH)
        for line in lines:
            # we have 8-byte(64-bit) stored per register address, each value splited by whitespace is 4-byte(32-bit).
            # And there are 1 register address and 8 values per line
            this_line_list = ut.crash_dump_line_to_addr_val_pair(tag_next_level, line, cls.ENDIANNESS, byte_per_reg, cls.BYTE_PER_VAL, cls.VAL_PER_LINE)

            crash_dump_reg_list.extend(this_line_list)
        if cls.DEBUG_MODE is True:
            print tag + '[reg address] [reg value] after processing crash dump:'
            addr_formater = '{:0%dx}' % (cls.BYTE_PER_VAL << 1)
            val_formater = '{:0%dx}' % (byte_per_reg << 1)
            for reg_addr, reg_val in crash_dump_reg_list:
                print addr_formater.format(reg_addr) + ' ' + ' ' + val_formater.format(reg_val)
        return crash_dump_reg_list

class HQA_WORD(object):
    # The following vars are string used in MSGU parsers 
    W_IB = 'IB'
    W_OB = 'OB'
    W_ADMIN = 'Admin'
    W_OPER = 'Oper'
    W_HBA = 'HBA'
    W_RAID = 'RAID'
    W_ENABLE = 'enable'
    W_DISABLE = 'disable'
    W_NA = 'N/A'
    W_OFF = 'off'
    W_ON = 'on'
    W_MSIX = 'MSIx'
    W_INTX = 'INTx'
    # default queue id for HQA, should be a negative number
    DEFAULT_ID = -1
