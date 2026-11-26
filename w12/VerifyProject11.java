import java.nio.file.Path;

import Hack.VMEmulator.VMEmulator;
import builtInVMCode.Output;

/** Drive the bundled emulator and check the six official Project 11 programs. */
class VerifyProject11 {
    private static final int KEYBOARD = 24576;
    private static final int SCREEN = 16384;
    private static final int ENTER = 128;
    private static final int RIGHT = 132;
    private static final String[] STEP = {"vmstep"};
    private static final int[][] FONT = loadFont();
    private final VMEmulator vm = new VMEmulator();

    VerifyProject11(Path directory) throws Exception {
        vm.setWorkingDir(directory.toFile());
        vm.setAnimationMode(2);
        vm.doCommand(new String[]{"load"});
    }

    private int ram(int address) throws Exception {
        return Integer.parseInt(vm.getValue("RAM[" + address + "]"));
    }

    private void writeRam(int address, int value) throws Exception {
        vm.setValue("RAM[" + address + "]", Integer.toString(value));
    }

    private void step(int count) throws Exception {
        for (int index = 0; index < count; index++) {
            vm.doCommand(STEP);
        }
    }

    @FunctionalInterface
    private interface Check {
        boolean passed() throws Exception;
    }

    private void until(Check condition, int limit, String message) throws Exception {
        for (int count = 0; count < limit; count += 1000) {
            if (condition.passed()) {
                return;
            }
            step(1000);
        }
        require(condition.passed(), message + " (last function: " + vm.getValue("currentFunction") + ")");
    }

    private void key(int code, int steps) throws Exception {
        writeRam(KEYBOARD, code);
        step(steps);
        writeRam(KEYBOARD, 0);
        step(steps);
    }

    private boolean pixel(int x, int y) throws Exception {
        return (ram(SCREEN + 32 * y + x / 16) & (1 << (x % 16))) != 0;
    }

    private boolean textAt(int row, int column, String text) throws Exception {
        for (int index = 0; index < text.length(); index++) {
            int cell = column + index;
            for (int y = 0; y < 11; y++) {
                int address = SCREEN + 32 * (1 + row * 11 + y) + cell / 2;
                int bits = (ram(address) >> (8 * (cell % 2))) & 255;
                if (bits != FONT[text.charAt(index)][y]) {
                    return false;
                }
            }
        }
        return true;
    }

    private static int[][] loadFont() {
        // Read the matching font from the emulator's Java implementation of the OS.
        try {
            Output.init();
            var field = Output.class.getDeclaredField("map");
            field.setAccessible(true);
            return (int[][]) field.get(null);
        } catch (ReflectiveOperationException error) {
            throw new IllegalStateException("Could not read the bundled Jack OS font", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private void seven() throws Exception {
        until(() -> vm.getValue("currentFunction").equals("Sys.halt"), 2_000_000, "Seven did not finish");
        require(textAt(0, 0, "7"), "Seven did not print 7");
    }

    private void convertToBin() throws Exception {
        int input = 0xA55A;
        writeRam(8000, (short) input);
        until(() -> vm.getValue("currentFunction").equals("Sys.halt"), 2_000_000, "ConvertToBin did not finish");
        for (int bit = 0; bit < 16; bit++) {
            int address = 8001 + bit;
            require(ram(address) == ((input >> bit) & 1), "Wrong bit at RAM[" + address + "]");
        }
    }

    private void square() throws Exception {
        until(() -> pixel(30, 30), 2_000_000, "Square did not draw");
        require(pixel(0, 0) && pixel(30, 30) && !pixel(0, 31), "Wrong initial square");
        key('X', 50_000);
        require(hasInkAtY(32), "The square did not grow to height 33");
        key('Z', 50_000);
        require(!hasInkAtY(32), "The square did not shrink again");
        key(RIGHT, 20_000);
        require(!pixel(0, 0) && hasInkAtY(0), "The square did not move right");
        writeRam(KEYBOARD, 'Q');
        step(10_000);
        writeRam(KEYBOARD, 0);
        until(() -> vm.getValue("currentFunction").equals("Sys.halt"), 50_000, "Square did not exit");
    }

    private boolean hasInkAtY(int y) throws Exception {
        for (int word = 0; word < 32; word++) {
            if (ram(SCREEN + 32 * y + word) != 0) {
                return true;
            }
        }
        return false;
    }

    private void average() throws Exception {
        for (int code : new int[]{'3', ENTER, '4', ENTER, '-', '2', ENTER, '1', '0', ENTER}) {
            until(() -> vm.getValue("currentFunction").equals("Keyboard.readChar"), 2_000_000,
                "Average did not wait for input " + code);
            key(code, 15_000);
        }
        until(() -> vm.getValue("currentFunction").equals("Sys.halt"), 500_000, "Average did not finish");
        require(textAt(4, 0, "The average is 4"), "Average did not print 4 for 4, -2, 10");
    }

    private void pong() throws Exception {
        until(() -> textAt(22, 0, "Score: 0"), 2_000_000, "Pong did not display the initial score");
        key(RIGHT, 18_000);
        until(() -> textAt(22, 0, "Score: 1"), 8_000_000, "Pong did not score on the first paddle hit");
    }

    private void complexArrays() throws Exception {
        until(() -> vm.getValue("currentFunction").equals("Sys.halt"), 3_000_000, "ComplexArrays did not finish");
        int[] expected = {5, 40, 0, 77, 110};
        for (int index = 0; index < expected.length; index++) {
            int value = expected[index];
            String line = "Test " + (index + 1) + ": expected result: " + value
                + "; actual result: " + value;
            require(textAt(index, 0, line), "ComplexArrays failed test " + (index + 1));
        }
    }

    public static void main(String[] args) throws Exception {
        Path directory = Path.of(args[0]);
        new VerifyProject11(directory.resolve("Seven")).seven();
        System.out.println("Seven: PASS (7)");
        new VerifyProject11(directory.resolve("ConvertToBin")).convertToBin();
        System.out.println("ConvertToBin: PASS (all 16 bits)");
        new VerifyProject11(directory.resolve("Square")).square();
        System.out.println("Square: PASS (move, grow, shrink, quit)");
        new VerifyProject11(directory.resolve("Average")).average();
        System.out.println("Average: PASS (4, -2, 10 -> 4)");
        new VerifyProject11(directory.resolve("Pong")).pong();
        System.out.println("Pong: PASS (paddle hit, score 1)");
        new VerifyProject11(directory.resolve("ComplexArrays")).complexArrays();
        System.out.println("ComplexArrays: PASS (5, 40, 0, 77, 110)");
    }
}
