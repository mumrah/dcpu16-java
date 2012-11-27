import java.io.InputStream;
import java.io.FileInputStream;

public class DCPU16 {

  // Registers
  final static byte A = (byte)0x00;
  final static byte B = (byte)0x01;
  final static byte C = (byte)0x02;
  final static byte X = (byte)0x03;
  final static byte Y = (byte)0x04;
  final static byte Z = (byte)0x05;
  final static byte I = (byte)0x06;
  final static byte J = (byte)0x07;
  final static byte SP = (byte)0x1b;
  final static byte PC = (byte)0x1c;
  final static byte EX = (byte)0x1d;

  // Stack
  final static byte PUSH = (byte)0x18;
  final static byte POP = (byte)0x18;
  final static byte PEEK = (byte)0x19;
  final static byte PICK = (byte)0x1a;

  // Instructions
  final static byte SET = (byte)0x01;
  final static byte ADD = (byte)0x02;
  final static byte SUB = (byte)0x03;
  final static byte MUL = (byte)0x04;
  final static byte MLI = (byte)0x05;
  final static byte DIV = (byte)0x06;
  final static byte DVI = (byte)0x07;
  final static byte MOD = (byte)0x08;
  final static byte MDI = (byte)0x09;
  final static byte IFE = (byte)0x12;
  final static byte IFN = (byte)0x13;

  // Special Instructions
  final static byte JSR = (byte)0x01;

  final static int offset = 32;
  final short[] program;
  final short[] memory = new short[32 + 65536]; // 0x10000 words of memory plus registers

  private volatile boolean skip;

  public DCPU16(short[] program) {
    this.program = program;
    memory[PC] = 0;
    memory[SP] = (short)0xffff;
  }

  public void run() {
    debug();
    while((memory[PC] < program.length)) {
      step();
      debug();
    }
  }

  public void debug() {
    System.err.println("A: " + memory[A] + " B: " + memory[B] + " C: " + memory[C] +
                       " X: " + memory[X] + " Y: " + memory[Y] + " Z: " + memory[Z] +
                       " I: " + memory[I] + " J: " + memory[J] +
                       " SP: " + memory[SP] + " PC: " + memory[PC] + " EX: " + memory[EX]);
  }

  public void dump() {
    String line;
    short s;
    for(int i=0; i<512; i++) {
      line = "";
      for(int j=0; j<128; j++) {
        s = memory[i*128 + j + offset];  
        if(s == 0) {
          line += ".";
        } else {
          line += s;
        }
      }
      System.out.println(line);
    }
  }

  public static int addr(int addr) {
    return (addr & 0xffff) + offset;
  }

  public static int addr(int addr, int offset) {
    return (addr & 0xffff) + (offset & 0xffff) + DCPU16.offset;
  }

  public static int uint32(int x) {
    return x & 0xffffffff;
  }

  public static int uint16(int x) {
    return x & 0xffff;
  }

  public static int uint8(int x) {
    return x & 0xff;
  }

  public short next_word() {
    return program[memory[PC]++];
  }

  public boolean step() {
    int ins = next_word() & 0xffff;
    byte o = (byte)(ins & 0x1f);
    byte b = (byte)((ins >> 5) & 0x1f);
    byte a = (byte)((ins >> 10) & 0x3f); 
    //System.err.println("a: " + a  + " b: " + b + " o: " + o);

    int u = 0, v = 0;
    double d;


    // The destination address (b)
    if(b < 0x08) { // register
      v = b;
    } else if(b < 0x10) { // [register]
      v = addr(memory[b - 0x08]);
    } else if(b < 0x18) { // [register + next_word]
      v = addr(memory[b - 0x10], next_word());
    } else if(b == PUSH) { // PUSH
      v = addr(--memory[SP]);
    } else if(b == PEEK) { // PEEK
      v = addr(memory[SP]);
    } else if(b == PICK) { // PICK next_word
      v = addr(memory[SP], next_word());
    } else if(b == SP) { // SP
      v = SP;
    } else if(b == PC) { // PC
      v = PC;
    } else if(b == EX) { // EX
      v = EX;
    } else if(b == 0x1e) { // [next_word]
      v = addr(next_word());
    } else if(b == 0x1f) { // next_word
      // Fail
      throw new RuntimeException("How'd we get here?");
    } else {
      // Fail
      throw new RuntimeException("How'd we get here?");
    }

    // The source (a), can be an address or literal
    if(a < 0x08) { // register
      u = memory[a];
    } else if(a < 0x10) { // [register]
      u = memory[addr(memory[a - 0x08])];
    } else if(a < 0x18) { // [register + next_word]
      u = memory[addr(memory[a - 0x10], next_word())];
    } else if(a == 0x18) { // POP
      u = memory[addr(memory[SP]++)];
    } else if(a == 0x19) { // PEEK
      u = memory[addr(memory[SP])];
    } else if(a == 0x1a) { // PICK next_word
      u = memory[addr(memory[SP], next_word())];
    } else if(a == SP) { // SP
      u = memory[SP];
    } else if(a == PC) { // PC
      u = memory[PC];
    } else if(a == EX) { // EX
      u = memory[EX];
    } else if(a == 0x1e) { // [next_word]
      u = memory[addr(next_word())];
    } else if(a == 0x1f) { // next_word
      u = next_word();
    } else if(a < 0x40) { // small_literal_value
      u = a - 0x21;
    } else {
      // Fail
      throw new RuntimeException("How'd we get here?");
    }

    if(skip) {
      System.err.println("skip");
      skip = false;
      return true;
    }

    v = v & 0xfffff;
    //System.err.println("u(a): " + u + " v(b): " + v + " memory[v(b)]: " + memory[v]);

    int x, y;
    switch(o) {
      case 0x00:
        switch(b) {
          case JSR:
            System.err.println("JSR");
            memory[PC] = (short)(u & 0xffff);
            return true;
          default:
            System.err.println("ERR");
            return false;
        }
      case SET:
        System.err.println("SET");
        memory[v] = (short)(u & 0xffff);
        return true;
      case ADD:
        System.err.println("ADD");
        System.err.println(memory[v] + " " + uint16(u));
        x = uint16(memory[v]) + uint16(u);
        memory[v] = (short)(x & 0xffff);
        memory[EX] = (short)((x >> 16) & 0xffff);
        return true;
      case SUB:
        System.err.println("SUB");
        if(v == PC) {
          x = uint16(memory[v]) - uint16(u) - 1;
        } else {
          x = uint16(memory[v]) - uint16(u);
        }
        memory[v] = (short)(x & 0xffff);
        memory[EX] = (short)((x >> 16) & 0xffff);
        return true;
      case MUL:
        System.err.println("MUL");
        x = uint16(memory[v]) * uint16(u);
        memory[v] = (short)(x & 0xffff);
        memory[EX] = (short)((x >> 16) & 0xffff);
        return true;
      case MLI:
        System.err.println("MLI");
        x = memory[v] * (short)u;
        memory[v] = (short)(x & 0xffff);
        memory[EX] = (short)((x >> 16) & 0xffff);
        return true;
      case DIV:
        System.err.println("DIV");
        if(u == 0) {
          memory[v] = 0;
          memory[EX] = 0;
        } else {
          x = uint16(memory[v]) / uint16(u);
          memory[v] = (short)x;
          memory[EX] = (short)((x << 16) & 0xffff);
        }
        return true;
      case DVI:
        System.err.println("DVI");
        if(u == 0) {
          memory[v] = 0;
          memory[EX] = 0;
        } else {
          x = memory[v] / (short)u;
          memory[v] = (short)x;
          memory[EX] = (short)((x << 16) & 0xffff);
        }
        return true;
      case MOD:
        System.err.println("MOD");
        memory[v] = (short)((uint16(memory[v]) % uint16(u)) & 0xffff);
        return true;
      case MDI:
        System.err.println("MDI");
        memory[v] = (short)((memory[v] % (short)u) & 0xffff);
        return true;
      case AND:
        System.err.println("AND");
        memory[v] = (short)(memory[v] & u);
        return true;
      case BOR:
        System.err.println("BOR");
        memory[v] = (short)(memory[v] | u);
        return true;
      case XOR:
        System.err.println("XOR");
        memory[v] = (short)(memory[v] ^ u);
        return true;
      case IFE:
        System.err.println("IFE");
        skip = !(memory[v] == u);
        return true;
      case IFN:
        System.err.println("IFN");
        skip = (memory[v] == u);
        return true;
      default:
        System.err.println("ERR");
        return false;
    }
  }
  
  public static short encode(int o, int b, int a) {
    return (short)(((a & 0x3f) << 10) | ((b & 0x1f) << 5) | (o & 0x1f));
  }

  public static void main(String[] args) throws Exception {
    InputStream in = new FileInputStream(args[0]);
    byte[] word = new byte[2];
    short[] buffer = new short[65535];
    int i = 0;
    while(in.read(word) != -1) {
      // Little-endian byte order
      buffer[i++] = (short)((uint8(word[1]) << 8) | uint8(word[0]));
    }   
    short[] program = new short[i];
    System.arraycopy(buffer, 0, program, 0, program.length);
    DCPU16 cpu = new DCPU16(program);

    /*
    DCPU16 cpu = new DCPU16(new short[]{
      encode(SET, B, 0x1f), 42,        // SET B, 42
      encode(SET, A, 0x1f), 41,        // SET A, 41
      encode(SET, A, B),               // SET A, B
      encode(SET, A + 0x08, 0x1f), 43, // SET [A], 43
      encode(SET, C, A + 0x08),        // SET C, [A]
      encode(SET, A, 0x1e), 42,        // SET A, $42
      encode(SET, 0x1f, 0x1f), 44, 43, // SET $43, 44
      encode(SET, B, A + 0x08),        // SET B, [A]
      encode(ADD, B, A),               // ADD B, A
      encode(ADD, B, 0x1f), 10,        // ADD B, 10
      encode(SUB, B, A),               // SUB B, A
      encode(IFE, B, A),               // IFE B, A
      encode(ADD, A, B),               //   ADD A, B
      encode(SET, B, A),               // SET B, A
      encode(IFE, B, A),               // IFE B, A
      encode(ADD, A, 0x1f), 10,        //   ADD A, 10
      encode(SET, PUSH, 0x1f), 10,     // SET PUSH, 10
      encode(SET, PUSH, 0x1f), 11,     // SET PUSH, 11
      encode(SET, C, PICK), 1,         // SET C, PEEK 1
      encode(SET, B, POP),             // SET B, POP
      encode(MUL, B, C),               // MUL B, C
      encode(MLI, B, 0x1f), -1,
      encode(ADD, A, B),
    });
    */
    cpu.run();
    cpu.dump();
  }
}
