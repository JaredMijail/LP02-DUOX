import ply.lex as lex

class LinkerLoader:
    def __init__(self, programa, programStart):
        self.lexer = lex.lex(object=self)
        self.programStart = programStart
        self.dirs = {}
        self.data = programa
        self.dirStart = 2000
            
    def build(self):
        self.lexer = lex.lexer(self)
    
    def parseFile(self):

        self.data = self.data.splitlines()
        for i in range(len(self.data)):
            lastToken = self.data[i].split(" ")[-1]
            self.lexer.input(lastToken)
            token = self.lexer.token()
            if token:
                if token.type == "LABELNEEDED":
                    self.addAbsLabel(i)
                if token.type == "DIRNEEDED":
                    self.addAbsDir(i)

    def addAbsLabel(self, index):
        string = self.data[index].split(" ")
        label = string[-1].strip("{}")
        label = self.hexHelper(int(label)+ self.programStart)
        key = "{}".format(label)
        string[-1] = key
        self.data[index] = self.data[index][0:3] + label

    def addAbsDir(self, index):
        string = self.data[index].split(" ")
        print(string)
        label = ord(string[-1].strip("{}")) - 65
        label = str(int(label)*100 + self.dirStart)
        key = "00 00 00 00 00 00 {} {}".format(label[0:2], label[2:4])
        string[-1] = key
        self.data[index] = " ".join(string)

    def showResult(self):
        for i in range(len(self.data)):
            print(self.data[i])

    #-----------Lexer-----------------

    tokens = (
         'READY', 'DIRNEEDED', 'LABELNEEDED'
        )

    def t_READY(self, t):
         r'([0-9][0-9]|\s|[0-9])+'
         return t
    
    def t_DIRNEEDED(self,t):
        r'\{[a-zA-Z]+\}'
        return t

    def t_LABELNEEDED(self,t):
        r'\{[0-9]+\}'
        return t

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

    def hexHelper(self, int):
        hex_string = '0x{:02x}'.format(int).split('x')[-1] 
        string = ["00" ,"00" ,"00", "00", "00", "00", "00", "00"]
        hexList = [hex_string[i:i+2] for i in range(0,len(hex_string),2)][::-1]
        i = len(hexList) -1
        while i>=0:
            string[-i-1] = hexList[i]
            i -= 1

        string = " ".join(string)
        return string
        



#Programa de prueba, calculo de factorial de 5 a absoluto
data = '''
10 00 00 00 00 00 00 00 05
15 {A}
10 00 00 00 00 00 00 00 06
10 00 00 00 00 00 00 00 01
15 {B}
14 {A}
21 00 00 00 00 00 00 00 {128}
14 {B}
14 {A}
03
15 {B}
14 {A}
10 00 00 00 00 00 00 00 01
02
15 {A}
20 00 00 00 00 00 00 00 {54}
27
'''

#Resultado del lexerAssembler del calculo de 5 factorial.
file = open("resultLexer.txt", "r")
data = file.read()
file.close()

#El inicio del programa debe ser el mismo que el del archivo config
asm = LinkerLoader(data, 0x1000)
asm.parseFile()
asm.showResult()
f = open("resultLinker.txt", "x")
for i in range(len(asm.data)):
    f.write(asm.data[i])
    f.write("\n")  


