import ply.lex as lex
import os 

class Preprocesador:
    def __init__(self, programa):
            self.lexer = lex.lex(object=self)
            self.macros = {}
            self.includes = {}
            self.libraries = set()
            self.programa = programa

    tokens = (
        'INCLUDE',
        'DEFINE',
        'MACRO'
        )

        # Regular expression rules for simple tokens
    t_INCLUDE = r'\#include\s+<([a-zA-Z_.]|[0-9])+.?[a-z]+>'

        # A regular expression rule with some action code
    def t_NUMBER(self,t):
        r'\d+'
        t.value = int(t.value)    
        return t

    def t_DEFINE(self, t):
        r'\#define\s+[A-Z_]+\s+([0-9]+|\"([a-zA-Z]+|[0-9])+\")'
        
    # Define a rule so we can track line numbers
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore  = ' \t'

    # Error handling rule
    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def parseFile(self):
        for line in self.programa:
            if line[0] == "#":
                token = self.lexer.input()
                print(token)
            else:
                continue
            

    def addMacro(self, var, val):
        self.macros[var] = val;


    def get(self, var):
        return self.macros.get(var)



file = open("programa.txt", "r")

pre = Preprocesador(file)
lexe = pre.lexer


# Give the lexer some input

pre.parseFile()
print(pre.macros)