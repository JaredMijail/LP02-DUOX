import ply.lex as lex

class Assembler:
    def __init__(self, programa):
            self.lexer = lex.lex(object=self)
            self.label = {}
            self.programa = programa
            self.pcCounter = 0
            self.dirCounter = 0
            self.result = []

    def build(self):
            self.lexer = lex.lexer(self)
    
    def parseFile(self):
        self.lexer.input(self.programa)
        #Primera pasada, Convierte en lenguaje de maquina
        while True:
            token = self.lexer.token()

            if not token:
                break
            self.result.append(token)

        #Segunda pasada, retorna con las etiquetas 
        for i in range(len(self.result)):
            self.lexer.input(self.result[i])
            token = self.lexer.token()
            if token:
                if token.type == "UNFINISHED_LABEL":
                    self.completeLabel(i)
            
    
    def completeLabel(self, index):
        string = self.result[index].split(" ")
        label = string[-1].strip("{}")
        key = "{{{}}}".format(self.label[label])
        string[-1] = key
        self.result[index] = " ".join(string)


    def showResult(self):
        for i in range(len(self.result)):
            print(self.result[i])
        print(self.label)

    #-----------Lexer-----------------

    tokens = (
        'NOP', 'ADD','SUB','MUL', 'DIV', 'MOD',
        'AND', 'OR', 'XOR', 'NOT', 'SHL', 'SHR'
        'PUSH', 'POP', 'DUP', 'SWAP', 'LOAD', 'STORE', 'LOAD_OFF',
        'STORE_OFF', 'LOAD_IMM',
        'JMP','JZ', 'JGT', 'JLT', 'CALL', 'RET', 'HALT',
        'GET_CORE', 'LOCK', 'UNLOCK', 'CORE_START', 'CORE_YIELD',
        'IN_PORT', 'OUT_PORT', 'NET_SEND', 'NET_RECV', 'NET_STAT', 'OUT',
        'CACHE_FLUSH', 'MEM_COPY', 'SET_FLAGS', 'GET_FLAGS', 'INT', 'IRET',
        'EI', 'DI'
        "LABEL", 'UNFINISHED_LABEL', "TUPLA", 'UNFINISHED_DIR'
        )

    t_TUPLA = r'([0-9][0-9]|\s)+'
    
    def t_UNFINISHED_LABEL(self, t):
        r'2[0-5]\s([0-9][0-9]|\s)+\{[a-zA-Z]+\}'
        return t

    def t_LABEL(self, t):
        r'[a-zA-z]+:'
        value = t.value[:-1]
        self.label[value] = self.pcCounter
        return 

    #Instrucciones aritmeticas
    def t_NOP(self,t):
        r'NOP'
        return '00'

    def t_ADD(self,t):
        r'ADD'
        return '01'

    def t_SUB(self,t):
        r'SUB'
        self.pcCounter += 1
        return '02'
    
    def t_MUL(self,t):
        r'MUL'
        self.pcCounter += 1
        return '03'

    def t_DIV(self,t):
        r'DIV'
        return '04'

    def t_MOD(self,t):
        r'MOD'
        return '05'

    #Instrucciones logicas
    def t_AND(self,t):
        r'AND'
        return '06'
    
    def t_OR(self,t):
        r'OR'
        return '07'
    
    def t_XOR(self,t):
        r'XOR'
        return '08'

    def t_NOT(self,t):
        r'NOT'
        return '09'

    def t_SHL(self,t):
        r'SHL'
        return '0A'
    
    def t_SHR(self,t):
        r'SHR'
        return '0B'

    #Pila y memoria

    def t_PUSH(self,t):
        r'PUSH\s[0-9]+'
        self.pcCounter += 9
        value  = t.value.split(" ")[-1]
        return '10 00 00 00 00 00 00 00 0{}'.format(value)
    
    def t_POP(self,t):
        r'POP'
        return '11'

    def t_DUP(self,t):
        r'DUP'
        return '12'

    def t_SWAP(self,t):
        r'SWAP'
        return '13'

    def t_LOAD(self,t):
        r'LOAD\s[A-Z]+'
        self.pcCounter += 9
        value  = t.value.split(" ")[-1]
        
        return '14 {{{}}}'.format(value)

    def t_STORE(self,t):
        r'STORE\s[A-Z]+'
        self.pcCounter += 9
        value  = t.value.split(" ")[-1]
        
        return '15 {{{}}}'.format(value)
    
    def t_LOAD_OFF(self,t):
        r'LOAD_OFF\s[A-Z]+'
        value  = t.value.split(" ")[-1]
        return '16 {{{}}}'.format(value)

    def t_STORE_OFF(self,t):
        r'LOAD\s[A-Z]+'
        value  = t.value.split(" ")[-1]
        
        return '17 {{{}}}'.format(value)

    def t_LOAD_IMM(self,t):
        r'LOAD\s[A-Z]+'
        value  = t.value.split(" ")[-1]
        
        return '18 {{{}}}'.format(value)
 
    #Bifurcaciones
    def t_JMP(self,t):
        r'JMP\s[a-zA-Z]+'
        value  = t.value.split(" ")[-1]
        
        return '20 00 00 00 00 00 00 00 {{{}}}'.format(value)
    
    def t_JZ(self,t):
        r'JZ\s[a-zA-Z]+'
        self.pcCounter += 18
        value  = t.value.split(" ")[-1]
        
        return '21 00 00 00 00 00 00 00 {{{}}}'.format(value)

    def t_JNZ(self,t):
        r'JNZ\s[a-zA-Z]+'
        value  = t.value.split(" ")[-1]
        
        return '22 00 00 00 00 00 00 00 {{{}}}'.format(value)

    def t_JGT(self,t):
        r'JGT\s[a-zA-Z]+'
        value  = t.value.split(" ")[-1]
        return '23 00 00 00 00 00 00 00 {{{}}}'.format(value)

    def t_JLT(self,t):
        r'JLT\s[a-zA-Z]+'
        value  = t.value.split(" ")[-1]
        return '24 00 00 00 00 00 00 00 {{{}}}'.format(value)

    def t_CALL(self,t):
        r'CALL\s[a-zA-Z]+'
        value  = t.value.split(" ")[-1]
        return '25 00 00 00 00 00 00 00 {{{}}}'.format(value)

    def t_RET(self,t):
        r'RET'
        return '26'

    def t_HALT(self,t):
        r'HLT'
        return '27'

    #Operaciones con nucleos
    def t_GET_CORE(self,t):
        r'GET_CORE'
        return '30'
    
    def t_LOCK(self,t):
        r'LOCK'
        return '31'
    
    def t_UNLOCK(self,t):
        r'UNLOCK'
        return '32'
    
    def t_CORE_START(self,t):
        r'CORE_START'
        return '33'
    
    def t_CORE_YIELD(self,t):
        r'CORE_YIELD'
        return '34'

    #Operaciones de comunicación
    def t_IN_PORT(self,t): 
        r'IN_PORT'
        return '40'
    
    def t_OUT_PORT(self,t):
        r'OUT_PORT'
        return '41'
    
    def t_NET_SEND(self,t): 
        r'NET_SEND'
        return '42'
    
    def t_NET_RECV(self,t): 
        r'NET_RECV'
        return '43'
    
    def t_NET_STAT(self,t): 
        r'NET_STAT'
        return '44'
    
    def t_OUT(self,t):
        r'OUT'
        return '45'

    #Memoria
    def t_CACHE_FLUSH(self,t):
        r'CACHE_FLUSH'
        return '50'

    def t_MEM_COPY(self,t):
        r'MEM_COPY'
        return '51'
     
    def t_SET_FLAGS(self,t):
        r'SET_FLAGS' 
        return '52'
    
    def t_GET_FLAGS(self,t):
        r'GET_FLAGS'
        return '53'
     
    def t_INT(self,t):
        r'INT'
        return '54'
    
    def t_IRET(self,t):  
        r'IRET'
        return '55'
    
    def t_EI(self,t):  
        r'EI'
        return '56'
    
    def t_DI(self,t):
        r'DI'
        return '57'

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

#Programa de prueba, calculo de 5 factorial
file = open("Factorial5assemblerEtiquetas.txt", "r")
data = file.read()
file.close()
asm = Assembler(data)
asm.parseFile()
asm.showResult()
f = open("resultLexer.txt", "x")
for i in range(len(asm.result)):
    f.write(asm.result[i])
    f.write("\n")

