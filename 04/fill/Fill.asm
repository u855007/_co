// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed.
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

(LOOP)
    @KBD
    D=M
    @BLACK
    D;JNE    // If KBD != 0, go to BLACK

(WHITE)
    @color
    M=0     // color = white
    @FILL
    0;JMP

(BLACK)
    @color
    M=-1    // color = black
    @FILL
    0;JMP

(FILL)
    @SCREEN
    D=A
    @address
    M=D     // address = SCREEN base address

(FILL_LOOP)
    @color
    D=M
    @address
    A=M
    M=D     // RAM[address] = color

    @1
    D=A
    @address
    M=M+D   // address++

    @24576
    D=A
    @address
    D=D-M
    @END_FILL
    D;JLE    // If address >= 24576, stop filling

    @FILL_LOOP
    0;JMP

(END_FILL)
    @LOOP
    0;JMP
