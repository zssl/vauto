#Modified by zhangsheng for automatic verilog writing
#Based vTbgenerator.py, Verilog Automatic
#

import os
import sublime
import sublime_plugin

import re
import sys
import time

def delComment( Text ):
    """ removed comment """
    single_line_comment = re.compile(r"//(.*)$", re.MULTILINE)
    multi_line_comment  = re.compile(r"/\*(.*?)\*/",re.DOTALL)
    Text = multi_line_comment.sub('\n',Text)
    Text = single_line_comment.sub('\n',Text)
    return Text

def delBlock( Text ) :
    """ removed task and function block """
    Text = re.sub(r'\Wtask\W[\W\w]*?\Wendtask\W','\n',Text)
    Text = re.sub(r'\Wfunction\W[\W\w]*?\Wendfunction\W','\n',Text)
    return Text

def findName(inText):
    """ find module name and port list"""
    p = re.search(r'([a-zA-Z_][a-zA-Z_0-9]*)\s*',inText)
    mo_Name = p.group(0).strip()
    return mo_Name

def paraDeclare(inText ,portArr) :
    """ find parameter declare """
    pat = r'\s'+ portArr + r'\s[\w\W]*?;'
    ParaList = re.findall(pat ,inText)

    return ParaList

def portDeclare(inText ,portArr) :
    """find port declare, Syntax:
       input [ net_type ] [ signed ] [ range ] list_of_port_identifiers

       return list as : (port, [range])
    """
    port_definition = re.compile(
        r'\b' + portArr +
        r''' (\s+(wire|reg)\s+)* (\s*signed\s+)*  (\s*\[.*?:.*?\]\s*)*
        (?P<port_list>.*?)
        (?= \binput\b | \boutput\b | \binout\b | ; | \) )
        ''',
        re.VERBOSE|re.MULTILINE|re.DOTALL
    )

    pList = port_definition.findall(inText)

    t = []
    for ls in pList:
        if len(ls) >=2  :
            t = t+ portDic(ls[-2:])
    return t

def portDic(port) :
    """delet as : input a =c &d;
        return list as : (port, [range])
    """
    pRe = re.compile(r'(.*?)\s*=.*', re.DOTALL)

    pRange = port[0]
    pList  = port[1].split(',')
    pList  = [ i.strip() for i in pList if i.strip() !='' ]
    pList  = [(pRe.sub(r'\1', p), pRange.strip() ) for p in pList ]

    return pList

def formatPort(AllPortList,isPortRange =1) :
    PortList = AllPortList[0] + AllPortList[1] + AllPortList[2]

    str =''
    if PortList !=[] :
        l1 = max([len(i[0]) for i in PortList])+2
        l2 = max([len(i[1]) for i in PortList])
        l3 = max(24, l1)

        strList = []
        for pl in AllPortList :
            if pl  != [] :
                str = ',\n'.join( [' '*4+'.'+ i[0].ljust(l3)
                                  + '( '+ (i[0].ljust(l1 )+i[1].ljust(l2))
                                  + ' )' for i in pl ] )
                strList = strList + [ str ]

        str = ',\n\n'.join(strList)

    return str


def formatDeclare(PortList,portArr, initial = "" ):
    str =''
    if initial !="" :
        initial = " = " + initial

    if PortList!=[] :
        str = '\n'.join( [ portArr.ljust(4) +'  '+(i[1]+min(len(i[1]),1)*'  '
                           +i[0]).ljust(36)+ initial + ' ;' for i in PortList])
    return str
###formatPortDeclare modify###
def formatPortDeclare(PortList,portArr):
    str =''
    if PortList!=[] :
        str = ',\n'.join( [ '  '+portArr.ljust(4) +'  '+(i[1].rjust(12)+min(len(i[1]),1)*'  '
                           +i[0]).ljust(36) for i in PortList])
    return str
###formatPortDeclare modify###

def formatPara(ParaList) :
    paraDec = ''
    paraDef = ''
    if ParaList !=[]:
        s = '\n'.join( ParaList)
        pat = r'([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*([\w\W]*?)\s*[;,]'
        p = re.findall(pat,s)

        l1 = max([len(i[0] ) for i in p])
        l2 = max([len(i[1] ) for i in p])
        paraDec = '\n'.join( ['parameter %s = %s;'
                             %(i[0].ljust(l1 +1),i[1].ljust(l2 ))
                             for i in p])
        paraDef =  '#(\n' +',\n'.join( ['    .'+ i[0].ljust(l1 +1)
                    + '( '+ i[1].ljust(l2 )+' )' for i in p])+ '\n)\n'

    return paraDec,paraDef

def format_out() :
    inText = sublime.get_clipboard()
    inText = delComment(inText)
    inText = delBlock  (inText)
    moPos_begin = re.search(r'(\b|^)module\b', inText ).end()
    moPos_end   = re.search(r'\bendmodule\b', inText ).start()
    inText = inText[moPos_begin:moPos_end]
    name  = findName(inText)
    paraList = paraDeclare(inText,'parameter')
    paraDec , paraDef = formatPara(paraList)
    ioPadAttr = [ 'input','output','inout']
    input  =  portDeclare(inText,ioPadAttr[0])
    output =  portDeclare(inText,ioPadAttr[1])
    inout  =  portDeclare(inText,ioPadAttr[2])
    tb_in_wire  = formatDeclare(input , 'wire ')
    tb_out_wire = formatDeclare(output , 'wire ')
    #generate out data
    in_wire  = formatDeclare(input , 'wire ')
    out_wire = formatDeclare(output , 'wire ')
    portList = formatPort( [input , output , inout] )
    stiPortList = formatPort( [input, output, inout] )
    input  = formatPortDeclare(input ,'output reg')
    output = formatPortDeclare(output ,'input         ')
    inout  = formatPortDeclare(inout ,'inout')
    return name, paraDef, in_wire, out_wire, portList, stiPortList, input, output, inout


def check_file_ext(file_name):
    ext_name = os.path.splitext(file_name)[1]
    if ext_name != '.v' and ext_name != '.V':
        sublime.status_message(
            'This file "' + file_name + '" is not a verilog file !')
        raise Exception(
            'This file "' + file_name + '" is not a verilog file !')




    


class vauto_inst(sublime_plugin.TextCommand):
    def run(self, edit) :
        name, paraDef, in_wire, out_wire, portList, stiPortList, input, output, inout = format_out()
        vauto_inst_dat = name + "  " + paraDef + "  " + "inst_" + name + "\n" + portList + "\n);\n\n\n"
        for region in self.view.sel() : # put data to current cursor place
            self.view.insert(edit, region.begin(), vauto_inst_dat)
        


class vauto_wire(sublime_plugin.TextCommand):
    def run(self, edit):
        name, paraDef, in_wire, out_wire, portList, stiPortList, input, output, inout = format_out()
        vauto_wire_dat = in_wire +"\n" + out_wire +"\n\n\n"
        for region in self.view.sel() : # put data to current cursor place
            self.view.insert(edit, region.begin(), vauto_wire_dat)
        

class vauto_head(sublime_plugin.TextCommand):
    def run(self, edit):
        file_name = self.view.file_name()
        check_file_ext(file_name)
        file_name_without_path = os.path.split(file_name)[1]
        current_time = time.strftime('%Y-%m-%d %H:%M', time.localtime())
        file_head_other ='''//Department: MSD
//Description:
//Version------Designer------Coding------Simulate-----Review------Data
//v0.0     |               | zhangsheng |                       
//---------------------------------------------------------------------
//Version History
//v0.0:   draft'''
        self.view.insert(edit, 0, "\n//" + "-" * 98 + "\n")
        self.view.insert(edit, 0, "\n" + file_head_other)
        self.view.insert(edit, 0, "\n//Created On" + " " * 4 + ": " + current_time)
        self.view.insert(edit, 0, "\n//" + "\n//Filename" + " " * 6 + ": " + file_name_without_path)
        self.view.insert(edit, 0, "//" + "-" * 98 )


class vauto_tb(sublime_plugin.TextCommand):
    def run(self, edit) :
        name, paraDef, in_wire, out_wire, portList, stiPortList, input, output, inout = format_out()
        #print clock
        add_wave = '''add wave sim:/tb_IIR_Order1HP_DCRemoval/inst_sti_IIR_Order1HP_DCRemoval/reset '''
        timescale = '`timescale  1 ns / 10 ps\n'
        file_head = '''//---------------------------------------------------------------------
//Module Name:      .v
//Department: MSD
//Description:
//Version------Designer------Coding------Simulate-----Review------Data
//v0.0     |               | zhangsheng |                       
//---------------------------------------------------------------------
//Version History
//v0.0:   draft

'''
        clk_rst = '''
parameter TCLK=100;

initial begin
               rst_n = 1'b1;
  #3           rst_n = 1'b0;
  #1e4         rst_n = 1'b1;
end

initial begin
  clk = 1;
  forever begin
    #(TCLK/2)  clk=~rst_n;
    #(TCLK/2)  clk=1'b1;
  end
end

'''

 #check generate
        chk_filename = "chk_"+name+".v"
        if os.path.exists(chk_filename):
            sublime.status_message("check file existed\n")
        else:
            chk =open(chk_filename, 'w')
            chk.write(file_head)
            chk.write("\n")
            chk.write("module chk_%s(\n" % name)
            # list_of_port_declarations
            chk.write("// %s Outputs\n%s\n" % (name, output))
            chk.write(");\n\n")
            chk.write(clk_rst)
            chk.write("\nendmodule")
            chk.close()

#stimulus generate
        sti_filename = "sti_"+name+".v"
        if os.path.exists(sti_filename) :
            sublime.status_message("stimulus file existed\n")
        else :
            sti = open(sti_filename, 'w')
            # write stimulus
            sti.write(file_head);
            sti.write("\n" + timescale)
            sti.write("\n")
            sti.write("module sti_%s(\n" % name)
            # list_of_port_declarations
            sti.write("// %s Inputs\n%s\n"  % (name, input ))
            sti.write("// %s Outputs\n%s\n" % (name, output))
            #sti.write("// %s Bidirs\n%s\n"  % (name, inout ))
            sti.write(");\n\n")
            sti.write(clk_rst)
            sti.write("\nendmodule")
            sti.close()

    
#testbench generate
        tb_filename = "tb_"+name+".v"
        if os.path.exists(tb_filename) :
            sublime.status_message("testbench file existed\n")
        else :
            tb = open(tb_filename, 'w')
            tb.write(file_head)
            tb.write("module tb_%s();\n" % name)
            tb.write("// %s Inputs\n%s\n"  % (name, in_wire ))
            tb.write("// %s Outputs\n%s\n\n\n" % (name, out_wire))
            tb.write("sti_%s inst_sti_%s (\n%s\n);\n\n\n\n" %(name,name,stiPortList))
            tb.write("%s %s inst_%s (\n%s\n);" %(name,paraDef,name,portList))
            tb.write("\nendmodule")
            tb.close()


#wave list genrate
        wave_list_filename="wlist.tcl"
        if os.path.exists(wave_list_filename) :
            sublime.status_message("wave list file existed\n")
        else :
            wlist = open(wave_list_filename, 'w')
            wlist.write("add wave -in -group in sim:/tb_${TOP}/inst_${TOP}/* \n")
            wlist.write("add wave -out -group out sim:/tb_${TOP}/inst_${TOP}/* \n")
            wlist.close()
