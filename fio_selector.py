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

def get_drives():
    sample = ['/dev/nvme0n1','/dev/nvme1n1','/dev/nvme2n1']
    return sample

def create_fio(target):
    target_question = [
        {
            'type': 'list',
            'message': 'Select target drive',
            'name': 'target',
            'choices': target,
            'validate': lambda answer: 'You must choose one drive.' \
                if len(answer) == 0 else True
        }
    ]

    io_size_question = [
        {
            'type': 'list',
            'message': 'Select target IO transaction size',
            'name': 'io_size',
            'choices': ['4k','8k','16k','128k'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        }
    ]

    io_type_question = [
        {
            'type': 'list',
            'message': 'Select target IO transaction size',
            'name': 'io_type',
            'choices': ['random','sequential'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        }
    ]

    io_mix_question = [
        {
            'type': 'list',
            'message': 'Select target IO R/W mix',
            'name': 'io_mix',
            'choices': ['100% read','70% read','30% read','0% read'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        }
    ]

    qd_question = [
        {
            'type': 'list',
            'message': 'Select target IO Queue Depth',
            'name': 'QD',
            'choices': ['1','2','4','8','16','32','64','128','256'],
            'validate': lambda answer: 'You must choose one value.' \
                if len(answer) == 0 else True
        }
    ]
    answers = prompt(target_question, style=style)
    answers.update(prompt(io_size_question, style=style))
    answers.update(prompt(io_type_question, style=style))
    answers.update(prompt(io_mix_question, style=style))
    answers.update(prompt(qd_question, style=style))
    return (answers)

