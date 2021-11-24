import threading

PING_RESULT_AS_DICT = {}
PING_RESULT_AS_VAR = False
GLOBAL_VARS = {
    'PING_RESULT': False
}


def run_for_dict_parameter():
    PING_RESULT_AS_DICT['NAME'] = 'hello world'
    print('finish in ', run_for_dict_parameter.__name__)


def run_for_var_parameter():
    #GLOBAL_VARS['PING_RESULT'] = True
    global PING_RESULT_AS_VAR
    
    PING_RESULT_AS_VAR = True
    print('finish in ', run_for_var_parameter.__name__)


if __name__ == '__main__':
    threading.Thread(target=run_for_dict_parameter).start()
    threading.Thread(target=run_for_var_parameter).start()

    print('dict', PING_RESULT_AS_DICT)
    print('var', PING_RESULT_AS_VAR)
