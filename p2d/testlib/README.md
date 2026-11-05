# Testlib for DOMjudge

This copy of Mike Mirzayanov's C++ testlib adapts checker and interactor arguments, verdicts and feedback for DOMjudge. The converter includes it automatically with C++ (`.cpp`) validators, including files supplied through `--output-validator`. Set `TESTLIB_PATH` to use a directory containing an alternative `testlib.h`. See [LICENSE](LICENSE).

## Checker

Read the answer from `ans` and contestant output from `ouf`:

```cpp
#include "testlib.h"

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);
    int expected = ans.readInt();
    int actual = ouf.readInt();
    if (expected != actual)
        quitf(_wa, "expected %d, found %d", expected, actual);
    quitf(_ok, "answer is %d", expected);
}
```

DOMjudge calls `checker input_file answer_file feedback_directory < contestant_output`. The header maps acceptance to exit code 42 and wrong answers to 43.

## Interactor

Read test input from `inf`, send queries through standard output, and read contestant responses from `ouf`. The interactor must return the final verdict itself.

```cpp
#include "testlib.h"
#include <iostream>

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    int n = inf.readInt();
    for (int i = 0; i < n; ++i) {
        int a = inf.readInt();
        int b = inf.readInt();
        std::cout << a << " " << b << std::endl;
        int actual = ouf.readInt();
        if (actual != a + b)
            quitf(_wa, "query %d: expected %d, found %d", i + 1, a + b, actual);
    }
    quitf(_ok, "%d queries processed", n);
}
```

Flush after each query. DOMjudge does not run a separate checker over `tout`. For multi-pass setup, see [compatibility](../../README.md#compatibility).

## Package layout

The converter places the checker or interactor source and `testlib.h` in `output_validator/`. Legacy exports use `output_validators/checker/` or `output_validators/interactor/`.

For manual setup, upload a checker as a comparison executable or an interactor as a run executable, and enable the problem's interactive type for an interactor.
