#!/usr/bin/python
from __future__ import print_function, unicode_literals
from PyInquirer import style_from_dict, Token, prompt, Separator
from pprint import pprint



style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#f44336 bold',
    Token.Question: '',
})

def create_fio(target):
    questions = [
        {
            'type': 'list',
            'message': 'Select target drive',
            'name': 'target',
            'choices': target,
            'validate': lambda answer: 'You must choose one drive.' \
                if len(answer) == 0 else True
        },
    
        {
            'type': 'list',
            'message': 'Select target IO transaction size',
            'name': 'io_size',
            'choices': ['4k','8k','16k','32k','64k','128k','Other'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },
    
        {
            'type': 'input',
            'message': '\u2517\u2501 Enter target IO transaction size',
            'name': 'io_size',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['io_size'] == 'Other'
        }, 
    
        {
            'type': 'list',
            'message': 'Select target IO transaction random/sequential',
            'name': 'io_type',
            'choices': ['random','sequential'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },
    
        {
            'type': 'list',
            'message': 'Select target IO R/W mix',
            'name': 'io_mix',
            'choices': ['100% read','70% read','30% read','0% read'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },        

        {
            'type': 'list',
            'message': 'Select number of Jobs',
            'name': 'jobs',
            'choices': ['1','2','4','8','16','32','Other'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },
    
        {
            'type': 'input',
            'message': '\u2517\u2501 Enter number of jobs',
            'name': 'jobs',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['jobs'] == 'Other'
        },         

        {
            'type': 'list',
            'message': 'Select target IO Queue Depth',
            'name': 'QD',
            'choices': ['1','2','4','8','16','32','64','128','256','Other'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },

        {
            'type': 'input',
            'message': 'Select target IO Queue Depth',
            'name': 'QD',
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['QD'] == 'Other'
        },
           
        {
            'type': 'list',
            'message': 'Select target IO file size',
            'name': 'size',
            'choices': ['100%','50%','10%','100M','500M','1G','2G','10G','20G','Other'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        }, 
    
        {
            'type': 'input',
            'message': '\u2517\u2501 Enter target IO file size',
            'name': 'size',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['size'] == 'Other'
        },    
    
        {
            'type': 'list',
            'message': 'Select workload time',
            'name': 'time',
            'choices': ['10s','1m','1h','10h','2d','7d','10d','None','Other'    ],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        },     

        {
            'type': 'input',
            'message': '\u2517\u2501 Enter target workload time:',
            'name': 'time',
            'validate': lambda answer: 'You must enter a value.' \
                if len(answer) == 0 else True,
            'when': lambda answers: answers['time'] == 'Other'
        },

    ]
    answers = prompt(questions, style=style)
    return (answers)

