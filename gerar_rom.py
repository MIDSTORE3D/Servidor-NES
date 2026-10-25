"""Gera uma ROM NES original (mapper NROM-128) para demonstrar GitHub Pages + NFC.
Sem ROMs ou sprites comerciais. Uso livre. Execute: python gerar_rom.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).parent/'jogos'/'coleta-estrelas.nes'
OP={
 'SEI/imp':0x78,'CLD/imp':0xd8,'TXS/imp':0x9a,'INX/imp':0xe8,'DEX/imp':0xca,'TAX/imp':0xaa,'TAY/imp':0xa8,
 'TXA/imp':0x8a,'TYA/imp':0x98,'PHA/imp':0x48,'PLA/imp':0x68,'RTI/imp':0x40,'RTS/imp':0x60,'CLC/imp':0x18,'SEC/imp':0x38,
 'NOP/imp':0xea,'LSR/acc':0x4a,'BIT/abs':0x2c,
 'LDA/imm':0xa9,'LDA/zp':0xa5,'LDA/abs':0xad,'LDA/absx':0xbd,
 'LDX/imm':0xa2,'LDX/zp':0xa6,
 'LDY/imm':0xa0,
 'STA/zp':0x85,'STA/abs':0x8d,'STA/absx':0x9d,'STX/zp':0x86,'STX/abs':0x8e,
 'INC/zp':0xe6,'ROL/zp':0x26,
 'AND/imm':0x29,'ORA/imm':0x09,'EOR/imm':0x49,
 'ADC/imm':0x69,'SBC/imm':0xe9,'SBC/zp':0xe5,'CMP/imm':0xc9,'CPX/imm':0xe0,
 'BEQ/rel':0xf0,'BNE/rel':0xd0,'BCC/rel':0x90,'BCS/rel':0xb0,'BPL/rel':0x10,
 'JMP/abs':0x4c,'JSR/abs':0x20
}
class Assembler:
 def __init__(self,origin=0xc000):self.origin=origin;self.data=bytearray();self.labels={};self.refs=[]
 def addr(self):return self.origin+len(self.data)
 def label(self,name):
  if name in self.labels:raise ValueError('duplicate label '+name)
  self.labels[name]=self.addr()
 def emit(self,mn,mode='imp',v=None):
  self.data.append(OP[f'{mn}/{mode}'])
  if mode in ('imm','zp','rel','acc'):
   if mode=='acc':return
   if isinstance(v,str):self.refs.append((len(self.data),v,mode));self.data.append(0)
   else:self.data.append(v&0xff)
  if mode in ('abs','absx'):
   if isinstance(v,str):self.refs.append((len(self.data),v,mode));self.data.extend(b'\x00\x00')
   else:self.data.extend((v&255,(v>>8)&255))
 def r(self):
  for off,label,mode in self.refs:
   value=self.labels[label]
   if mode=='rel':
    rel=value-(self.origin+off+1)
    if not -128<=rel<=127:raise ValueError(f'Branch {label} range: {rel}')
    self.data[off]=rel&255
   elif mode in ('abs','absx'):self.data[off:off+2]=bytes((value&255,value>>8))
   else:self.data[off]=value&255
  if len(self.data)>0x3ffa:raise ValueError(f'Program too big ({len(self.data)})')
  b=bytearray(16384);b[:len(self.data)]=self.data
  for off,l in ((0x3ffa,'nmi'),(0x3ffc,'reset'),(0x3ffe,'reset')):
   v=self.labels[l];b[off:off+2]=bytes((v&255,v>>8))
  return b

a=Assembler()
I=lambda op,mode='imp',v=None:a.emit(op,mode,v)
L=a.label
# Zeropage: x=0, y=1, starx=2, stary=3, score=4, buttons=5, ones=6, tens=7.
L('reset')
I('SEI');I('CLD');I('LDX','imm',0x40);I('STX','abs',0x4017)
I('LDX','imm',0xff);I('TXS');I('INX')
for v in (0x2000,0x2001,0x4010):I('STX','abs',v)
I('BIT','abs',0x2002)
L('wait1');I('BIT','abs',0x2002);I('BPL','rel','wait1')
L('wait2');I('BIT','abs',0x2002);I('BPL','rel','wait2')
# Reset RAM and hide all sprites
I('LDX','imm',0)
L('clear_ram');I('LDA','imm',0)
for addr in (0x0000,0x0100,0x0300,0x0400,0x0500,0x0600,0x0700):I('STA','absx',addr)
I('LDA','imm',0xf8);I('STA','absx',0x0200)
I('INX');I('BNE','rel','clear_ram')
# initialize objects
for addr,val in [(0,112),(1,126),(2,183),(3,142),(4,0)]:I('LDA','imm',val);I('STA','zp',addr)
# write palette
I('LDA','imm',0x3f);I('STA','abs',0x2006);I('LDA','imm',0);I('STA','abs',0x2006)
I('LDX','imm',0)
L('pal_loop');I('LDA','absx','palette');I('STA','abs',0x2007);I('INX');I('CPX','imm',32);I('BNE','rel','pal_loop')
# write nametable + attribute table, 4 pages of 256 bytes each
I('LDA','imm',0x20);I('STA','abs',0x2006);I('LDA','imm',0);I('STA','abs',0x2006)
for idx in range(4):
 I('LDX','imm',0)
 L(f'nt_loop_{idx}');I('LDA','absx',f'nametable_{idx}');I('STA','abs',0x2007);I('INX');I('BNE','rel',f'nt_loop_{idx}')
# Init scroll and enable NMI / bg / sprites
I('LDA','imm',0);I('STA','abs',0x2005);I('STA','abs',0x2005)
I('LDA','imm',0x80);I('STA','abs',0x2000)
I('LDA','imm',0x1e);I('STA','abs',0x2001)
L('idle');I('JMP','abs','idle')

L('nmi');I('PHA');I('TXA');I('PHA');I('TYA');I('PHA')
I('JSR','abs','read_joy');I('JSR','abs','move_player');I('JSR','abs','collision');I('JSR','abs','draw_oam');I('JSR','abs','write_score')
I('LDA','imm',0);I('STA','abs',0x2005);I('STA','abs',0x2005)
I('PLA');I('TAY');I('PLA');I('TAX');I('PLA');I('RTI')

L('read_joy')
I('LDA','imm',1);I('STA','abs',0x4016)
I('LDA','imm',0);I('STA','abs',0x4016);I('STA','zp',5)
I('LDX','imm',8)
L('read_loop');I('LDA','abs',0x4016);I('LSR','acc');I('ROL','zp',5);I('DEX');I('BNE','rel','read_loop')
I('RTS')

L('move_player')
# Select to reset the score
I('LDA','zp',5);I('AND','imm',0x20);I('BEQ','rel','no_reset');I('LDA','imm',0);I('STA','zp',4)
L('no_reset')
# right bit0
I('LDA','zp',5);I('AND','imm',1);I('BEQ','rel','no_right')
I('LDA','zp',0);I('CMP','imm',234);I('BCS','rel','no_right');I('CLC');I('ADC','imm',2);I('STA','zp',0)
L('no_right')
I('LDA','zp',5);I('AND','imm',2);I('BEQ','rel','no_left')
I('LDA','zp',0);I('CMP','imm',20);I('BCC','rel','no_left');I('SEC');I('SBC','imm',2);I('STA','zp',0)
L('no_left')
I('LDA','zp',5);I('AND','imm',4);I('BEQ','rel','no_down')
I('LDA','zp',1);I('CMP','imm',218);I('BCS','rel','no_down');I('CLC');I('ADC','imm',2);I('STA','zp',1)
L('no_down')
I('LDA','zp',5);I('AND','imm',8);I('BEQ','rel','no_up')
I('LDA','zp',1);I('CMP','imm',64);I('BCC','rel','no_up');I('SEC');I('SBC','imm',2);I('STA','zp',1)
L('no_up');I('RTS')

L('collision')
# absolute difference in X and Y to detect collecting a star
I('LDA','zp',0);I('SEC');I('SBC','zp',2);I('BCS','rel','dx_ok');I('EOR','imm',255);I('CLC');I('ADC','imm',1)
L('dx_ok');I('CMP','imm',11);I('BCS','rel','no_hit')
I('LDA','zp',1);I('SEC');I('SBC','zp',3);I('BCS','rel','dy_ok');I('EOR','imm',255);I('CLC');I('ADC','imm',1)
L('dy_ok');I('CMP','imm',11);I('BCS','rel','no_hit')
I('INC','zp',4);I('LDA','zp',4);I('CMP','imm',100);I('BCC','rel','score_ok');I('LDA','imm',0);I('STA','zp',4)
L('score_ok')
# deterministic respawn new X and Y
I('LDA','zp',2);I('CLC');I('ADC','imm',73);I('CMP','imm',220);I('BCC','rel','x_check_low');I('SEC');I('SBC','imm',121)
L('x_check_low');I('CMP','imm',20);I('BCS','rel','new_x_ok');I('CLC');I('ADC','imm',31)
L('new_x_ok');I('STA','zp',2)
I('LDA','zp',3);I('CLC');I('ADC','imm',49);I('CMP','imm',215);I('BCC','rel','y_check_low');I('SEC');I('SBC','imm',145)
L('y_check_low');I('CMP','imm',69);I('BCS','rel','new_y_ok');I('CLC');I('ADC','imm',80)
L('new_y_ok');I('STA','zp',3)
L('no_hit');I('RTS')

L('draw_oam')
for src,dest in [(1,0x200),(0,0x203),(3,0x204),(2,0x207)]: I('LDA','zp',src);I('STA','abs',dest)
for dest,val in [(0x201,2),(0x202,0),(0x205,3),(0x206,1)]:I('LDA','imm',val);I('STA','abs',dest)
I('LDA','imm',0);I('STA','abs',0x2003)
I('LDA','imm',2);I('STA','abs',0x4014)
I('RTS')
L('write_score')
I('LDA','zp',4);I('LDX','imm',0)
L('div10');I('CMP','imm',10);I('BCC','rel','div_end');I('SEC');I('SBC','imm',10);I('INX');I('JMP','abs','div10')
L('div_end');I('STA','zp',6);I('STX','zp',7)
I('BIT','abs',0x2002)
I('LDA','imm',0x20);I('STA','abs',0x2006)
I('LDA','imm',0x71);I('STA','abs',0x2006)
I('LDA','zp',7);I('CLC');I('ADC','imm',16);I('STA','abs',0x2007)
I('LDA','zp',6);I('CLC');I('ADC','imm',16);I('STA','abs',0x2007)
I('RTS')

L('palette')
palette=[0x01,0x21,0x30,0x16, 0x01,0x2a,0x30,0x0f, 0x01,0x19,0x30,0x22, 0x01,0x2b,0x30,0x16,
         0x01,0x27,0x30,0x16, 0x01,0x38,0x30,0x19, 0x01,0x30,0x21,0x2c, 0x01,0x27,0x30,0x16]
a.data.extend(palette)
# Font tiles 32 = A, 33 = B ... and 16..25 = digits 0..9

def char_tile(ch):
 if ch==' ':return 0
 if ch.isdigit():return 16+int(ch)
 if ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':return 32+ord(ch)-65
 if ch==':':return 26
 if ch=='-':return 27
 return 0
board=[[0 for _ in range(32)] for _ in range(30)]
for x in range(32): board[0][x]=1;board[28][x]=1
for y in range(1,29):board[y][0]=1;board[y][31]=1
texts=[(2,9,'RETRO NFC NES'),(3,10,'PONTOS 00'),(5,6,'PEGUE AS ESTRELAS'),(26,7,'MOVIMENTAR SETAS'),(27,7,'SELECT ZERA OS PONTOS')]
for row,col,txt in texts:
 for j,ch in enumerate(txt):
  if col+j<31:board[row][col+j]=char_tile(ch)
for y in range(8,25,4):
 for x in range(3,30,6):
  board[y][x]=4
nt=[t for row in board for t in row]+[0]*64
assert len(nt)==1024
for idx in range(4):L(f'nametable_{idx}');a.data.extend(nt[idx*256:(idx+1)*256])
# Two-bit planar NES CHR tiles 0..511, each 16 bytes
chrdata=bytearray(8192)
def put_tile(index,pattern):
 assert len(pattern)==8 and all(len(row)==8 for row in pattern)
 off=index*16
 for y,row in enumerate(pattern):
  chrdata[off+y]=sum(((v&1)<<(7-x)) for x,v in enumerate(row))
  chrdata[off+8+y]=sum((((v>>1)&1)<<(7-x)) for x,v in enumerate(row))
put_tile(1,[[1]*8 for _ in range(8)])
put_tile(2,[
 [0,0,0,2,2,0,0,0],[0,0,2,2,2,2,0,0],[0,2,1,1,1,1,2,0],[2,2,2,2,2,2,2,2],
 [1,2,1,2,2,1,2,1],[1,0,1,2,2,1,0,1],[0,0,1,0,0,1,0,0],[0,1,0,0,0,0,1,0]])
put_tile(3,[
 [0,0,0,2,2,0,0,0],[0,0,2,2,2,2,0,0],[2,2,2,2,2,2,2,2],[0,2,2,1,1,2,2,0],
 [0,0,2,1,1,2,0,0],[0,2,2,2,2,2,2,0],[0,0,2,0,0,2,0,0],[0,0,0,0,0,0,0,0]])
put_tile(4,[
 [0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],[1,1,1,1,1,1,1,1],
 [1,1,1,1,1,1,1,1],[0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0]])
# Use Pillow only at build time for 8x8 glyph rasterization
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
font=ImageFont.truetype(fontpath,9)
for ch,i in [(str(n),16+n) for n in range(10)]+[(chr(65+n),32+n) for n in range(26)]+[(':',26),('-',27)]:
 im=Image.new('L',(8,8));d=ImageDraw.Draw(im);d.text((-1,-3),ch,font=font,fill=255,stroke_width=0)
 pattern=[[2 if im.getpixel((x,y))>95 else 0 for x in range(8)] for y in range(8)]
 put_tile(i,pattern)
# Add zp sbc opcode, which was only needed by collision; see dictionary definition below.
prg=a.r()
header=b'NES\x1a'+bytes([1,1,0,0])+bytes(8)
blob=header+prg+chrdata
assert len(blob)==16+16384+8192
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_bytes(blob)
print('ROM gerada:',OUT, 'Tamanho:',len(blob),'bytes','Code:',len(a.data),'bytes')
print('Reset:',hex(a.labels['reset']),'NMI:',hex(a.labels['nmi']))
