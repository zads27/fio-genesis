#!/usr/bin/python3

#Standard Libs
import os,glob

#Installed Libs
from PyInquirer import style_from_dict, Token, prompt, Separator

style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#f44336 bold',
    Token.Question: '',
})

def importFIO():
    #select/navigate directory
    #if file selected, return file name 
    #if directory or .. selected, change working dir and 
    answers = ''
    print ('')
    while True: 
        print('\x1b[A'+'\r')
        navigation = [
            {
                'type': 'list',
                'message': 'Current Directory:' + os.getcwd(),
                'name': 'selection',
                'choices': ['..'] + glob.glob('*/')
            }
        ]
        
        if glob.glob('*.fio'):
            navigation[0]['choices'] += [' *File in this directory:\n     '+'\n     '.join(glob.glob('*.fio'))] 
        answers = prompt(navigation, style=style)
        if '..' in answers['selection']:
            os.chdir('../')
        elif '.' not in answers['selection']:
            os.chdir(answers['selection'])
        else:
            break
    if 1:    
        selection= [        
            {
                'type': 'checkbox',
                'message': 'Select files, press Enter:',
                'name': 'selection',
                'choices': [{'name':x} for x in glob.glob(os.getcwd()+'/*.fio')],
                'validate': lambda answer: 'You must choose .' \
                    if len(answer) == 0 else True
            }
        ]
        answers = prompt(selection,style=style) 
        return answers
            

def create_fio(targets):
    print(targets)
    target = [x for x in targets if x]
    print(target)
    questions = [
        {
            'type': 'list',
            'message': 'Select target drive',
            'name': 'target',
            'choices': (target + ['*User defined target'])
        },
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter target drive/file',
            'name': 'target',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['target'] == '*User defined target'
        }, 

        {
            'type': 'list',
            'message': 'Select target IO transaction size',
            'name': 'io_size',
            'choices': ['4k','8k','16k','32k','64k','128k','Other']
        },
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter target IO transaction size',
            'name': 'io_size',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['io_size'] == 'Other'
        }, 
    
        {
            'type': 'list',
            'message': 'Select target IO transaction random/sequential',
            'name': 'io_type',
            'choices': ['random','sequential']
        },

        {
            'type': 'list',
            'message': 'Select target IO R/W mix',
            'name': 'io_mix',
            'choices': ['100% read','70% read','50% read','30% read','0% read','Custom %']
        },        
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter read percentage',
            'name': 'io_mix',
            'validate': lambda answer: 'You must enter a valid value (include %)' \
                if ((len(answer) == 0) or '%' not in answer) else True,
            'when': lambda answers: answers['io_mix'] == 'Custom %'
        },         
                        
                        
        {
            'type': 'list',
            'message': 'Select number of Jobs',
            'name': 'jobs',
            'choices': ['1','2','4','8','16','32','Other']
        },
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter number of jobs',
            'name': 'jobs',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['jobs'] == 'Other'
        },         

        {
            'type': 'list',
            'message': 'Select target IO Queue Depth',
            'name': 'QD',
            'choices': ['1','2','4','8','16','32','64','128','256','Other']
        },
        {
            'type': 'input',
            'message': 'Select target IO Queue Depth',
            'name': 'QD',
            'validate': lambda answer: 'You must enter one value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['QD'] == 'Other'
        },
           
        {
            'type': 'list',
            'message': 'Select target IO file size',
            'name': 'size',
            'choices': ['100%','50%','10%','100M','500M','1G','2G','10G','20G','Other']
        }, 
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter target IO file size',
            'name': 'size',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['size'] == 'Other'
        },    
    
        {
            'type': 'list',
            'message': 'Select workload time',
            'name': 'time',
            'choices': ['10s','1m','1h','10h','2d','7d','10d','None','Other']
        },     
        {
            'type': 'input',
            'message': u'\u2517\u2501 Enter target workload time:',
            'name': 'time',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['time'] == 'Other'
        }

    ]
    answers = prompt(questions, style=style)
    return (answers)

