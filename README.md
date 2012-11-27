# DCPU16 VM in Java

Python assembler, Java emulator.

he basic instructions are implemented, still working on subroutines. Have yet 
to look at the hardware stuff (if that's even officially spec'd out yet)

## Example - Count to 10

Assembly code
```asm
# count.asm
        SET I, 0
:loop   IFE I, 10
          SET PC, crash
        ADD I, 1
        SET PC, loop
:crash  SET A, 1        
        SET PC, crash
```

Compile to object code
```shell
python asm.py count.asm
```

Run the object code with the Java DCPU16 VM

```shell
java DCPU16 count.o
```

