"""
RISC-V ALU
(c) 2019 The Bonfire Project
License: See LICENSE
"""

from myhdl import *

from barrel_shifter import shift_pipelined
from instructions import ArithmeticFunct3  as f3 


class AluBundle:
    def __init__(self,xlen=32):
        self.funct3_i=Signal(intbv(0)[3:])
        self.funct7_6_i=Signal(bool(0))
        self.op1_i=Signal(modbv(0)[xlen:])
        self.op2_i=Signal(modbv(0)[xlen:])
        self.res_o=Signal(modbv(0)[xlen:])
        # Control Signals
        self.en_i=Signal(bool(0))
        self.busy_o=Signal(bool(0))
        self.valid_o=Signal(bool(0))

        # Constants
        self.xlen = xlen



    @block
    def alu(self,clock,reset, c_shifter_mode="none"):
        """
          c_shifter_mode:
            "none" : Don't implement shifts
            "comb" : Single cycle barrel shifter
            "pipelined" : 2-cycle barrel shifter
            "behavioral" : Implement shift with Python operators
        """

        assert ( c_shifter_mode=="none" or c_shifter_mode=="comb" or c_shifter_mode=="pipelined" or c_shifter_mode=="behavioral")
        #assert ( c_shifter_mode=="none" or c_shifter_mode=="behavioral")

        shifter_out = Signal(modbv(0)[self.xlen:])
        shift_valid = Signal(bool(0))
        shift_busy = Signal(bool(0))

        alu_valid = Signal(bool(0))

        if c_shifter_mode=="behavioral":

            @always_comb
            def shift():
                if self.funct3_i==f3.RV32_F3_SLL:
                    shifter_out.next = self.op1_i << self.op2_i[5:]
                    shift_valid.next=True
                elif self.funct3_i==f3.RV32_F3_SRL_SRA:
                    shifter_out.next =  ( self.op1_i.signed() if self.funct7_6_i else self.op1_i ) >>  self.op2_i[5:]
                    shift_valid.next=True
                else:
                     shift_valid.next=False

        elif c_shifter_mode=="comb" or c_shifter_mode=="pipelined":


            fill_v = Signal(bool(0))
            shift_en = Signal(bool(0))
            shift_ready = Signal(bool(0))
            shift_right = Signal(bool(0))

            shift_amount=Signal(intbv(0)[5:])



            shift_inst=shift_pipelined(clock,reset,self.op1_i,shifter_out,shift_amount, \
                       shift_right,fill_v,shift_en,shift_ready, 3 if c_shifter_mode=="pipelined" else 0 )
                      

            @always_comb
            def shift_comb():

                shift_valid.next = shift_ready
                shift_amount.next = self.op2_i[5:0]

                if self.funct3_i==f3.RV32_F3_SLL:
                    shift_right.next=False
                    fill_v.next=False
                    shift_en.next=not shift_busy and self.en_i
                elif self.funct3_i==f3.RV32_F3_SRL_SRA:
                    shift_right.next=True
                    fill_v.next=self.funct7_6_i and self.op1_i[self.xlen-1]
                    shift_en.next=not shift_busy and self.en_i
                else:
                   shift_right.next=False
                   fill_v.next=False
                   shift_en.next=False

            if c_shifter_mode=="pipelined":
                @always_comb
                def shift_pipelined_comb():
                    shift_busy.next = shift_ready


        @always_comb
        def comb():

            alu_valid.next=False
            

            if self.funct3_i==f3.RV32_F3_ADD_SUB:
                if self.funct7_6_i:
                    self.res_o.next = self.op1_i - self.op2_i
                else:
                    self.res_o.next = self.op1_i + self.op2_i
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_OR:
                self.res_o.next = self.op1_i | self.op2_i
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_AND:
                self.res_o.next = self.op1_i & self.op2_i
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_XOR:
                self.res_o.next = self.op1_i ^ self.op2_i
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_SLT:
                t_comp = self.op1_i.signed() < self.op2_i.signed()
                self.res_o.next =  concat( modbv(0)[31:], t_comp )
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_SLTU:
                t_comp = self.op1_i < self.op2_i
                self.res_o.next =  concat( modbv(0)[31:], t_comp  )
                alu_valid.next=self.en_i
            elif self.funct3_i==f3.RV32_F3_SLL or self.funct3_i==f3.RV32_F3_SRL_SRA:
                self.res_o.next = shifter_out.val
            else:
                assert False, "Invalid funct3_i"
                self.res_o.next = 0


        @always_comb
        def pipe_control():
            self.valid_o.next= alu_valid or shift_valid
            self.busy_o.next = shift_busy


        return instances()




