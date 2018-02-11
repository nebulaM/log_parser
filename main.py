import sys
import os
#sys.path.append(os.path.dirname(sys.argv[0]))
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AVAILABLE_PARSER_LIST = ['ossp', 'msgu']

def _main_help(script_name):
    print('Usage:\n')
    print('  python ' + script_name + ' [parser] [parser argvs...]')
    print('  [parser] can be one of [ossp], [msgu]')
    print('  ossp: translate OSSP register dump from input log')
    print('  msgu: translate MSGU register dump from input log')
    sys.exit(1)

if __name__ == '__main__':
    parser = ''
    if len(sys.argv) > 1 and sys.argv[1].lower() in AVAILABLE_PARSER_LIST:
        parser = sys.argv[1].lower()
        sys.argv[0] = sys.argv[0] + ' ' + parser 
        del sys.argv[1]
    else:
        _main_help(sys.argv[0])
    
    found_log_flag = False
    if parser == 'msgu':
        from src.msgu import msgu_log
        found_log_flag = msgu_log.run()

    elif parser == 'ossp':
        from src.ossp import ossp_log
        found_log_flag = ossp_log.run()
    # after the parser finished
    if found_log_flag:
        print('Please use a modern browser(other than Internet Explore) to view the result if possible.\n')
        print('If you view the result through Internet Explore, Javascript can be blocked by default.')
        print('A dialog box saying "Internet Explore restricts this webpage from running scripts or ActiveX controls" may appear at bottom of the webpage.')
        print('If this is the case, then please click the button saying "Allow blocked content" on that dialog box.')
    else:
        print('Found no log for ' + parser)
