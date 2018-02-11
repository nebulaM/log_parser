import os
import re
from ..shared import dutil as ut

class MSGULog(ut.XMLREToken):
    MODULE = 'msgu'
    SECTION = 'common'
    # common MSGU address offset to CPU address
    MSGU_ADDRESS_OFFSET = 0xbf400000

    ENDIANNESS = 'little'

    # chipset name
    LUXOR = 'Luxor'
    WF = 'WILDFIRE'

    # how many chars per line in dump file msgu section
    LOG_LINE_LENGTH = 82

    # how many byte per register value displayed on dump file
    BYTE_PER_VAL = 4
    # how many register value per register address is dumped on a line
    VAL_PER_LINE = 8

    # default chipset, this will be overwritten by calling set_chipset()
    chipset = LUXOR

    INPUT_DIR = ''
    OUTPUT_DIR = ''
    DEBUG_MODE = ''
    WORKSPACE = ''
    out_filename = ''

    @classmethod
    def set_input_params(cls):
        argv = _MSGU_DUMP_WORKER()
        argv.parse()
        cls.INPUT_DIR = argv.INPUT_DIR
        cls.OUTPUT_DIR =argv.OUTPUT_DIR
        cls.DEBUG_MODE = argv.DEBUG_MODE
        cls.WORKSPACE  = argv.WORKSPACE
        cls.out_filename = ut.get_parsed_filename(cls.INPUT_DIR, cls.MODULE) + '.html'
        cls.out_filename = os.path.join(cls.OUTPUT_DIR, cls.out_filename)

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
            print("From the input file, chipset is " + cls.chipset)
        else:
            print("Cannot read chipset from the input file, use default chipset " + cls.chipset)
    
    @classmethod
    def get_reg_val_list(cls, tag, header, ending, byte_per_reg):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'get_reg_val_list')
        reg_list = []
        lines = ut.save_line_to_list(tag_next_level, header, ending, \
        cls.INPUT_DIR, cls.LOG_LINE_LENGTH)
        for line in lines:
            # we have 8-byte(64-bit) stored per register address, each value splited by whitespace is 4-byte(32-bit).
            # And there are 1 register address and 8 values per line
            this_line_list = ut.reg_dump_line_to_addr_val_pair(tag_next_level, line, cls.ENDIANNESS, byte_per_reg, cls.BYTE_PER_VAL, cls.VAL_PER_LINE)

            reg_list.extend(this_line_list)
        if cls.DEBUG_MODE is True:
            print(tag + '[reg address] [reg value] after processing dump file:')
            addr_formater = '{:0%dx}' % (cls.BYTE_PER_VAL << 1)
            val_formater = '{:0%dx}' % (byte_per_reg << 1)
            for reg_addr, reg_val in reg_list:
                print(addr_formater.format(reg_addr) + ' ' + ' ' + val_formater.format(reg_val))
        return reg_list

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

class _MSGU_DUMP_WORKER(ut.DumpArgvWorker):
    '''@Override ut.DumpArgvWorker to parse sys argv for MSGU'''
    WORKSPACE = ''

    @classmethod
    def _set_workspace(cls, in_dir):
        ''' Set BC workspace, check this based on folder
            @param in_dir: path to a bc workspace
        '''
        if in_dir != '':
            if os.path.isdir(in_dir) and \
            os.path.isdir(os.path.join(in_dir, 'msgux')):
                cls.WORKSPACE = in_dir
            else:
                raise AssertionError('Error, [{}] is not a valid dir to a BC workspace because msgux folder is NOT under this folder.\n'.format(in_dir))

    @classmethod
    def _build(cls):
        ''' @Override
        '''
        parser = ut.DumpArgvWorker._build()
        parser.add_argument('-w', '--workspace', help='path to BaseCode workspace')
        return parser

    @classmethod
    def parse(cls, build_cb=None):
        ''' @Override
        '''
        if build_cb:
            args = ut.DumpArgvWorker.parse(build_cb)
        else:
            args = ut.DumpArgvWorker.parse(cls._build)
        cls._set_workspace(args.workspace)
        return args
