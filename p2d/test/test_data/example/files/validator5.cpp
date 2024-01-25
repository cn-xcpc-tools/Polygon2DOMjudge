#include <bits/stdc++.h>
#include "testlib.h"
using namespace std;
using ll = long long;

const int E4 = 10000;
const int E5 = 100000;
const int E9 = 1000000000;
const ll E18 = 1000000000000000000ll;

int main(int argc, char* argv[]) {
    registerValidation(argc, argv);
    int n = inf.readInt(0, 200, "n");
    inf.readEoln();
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < 8; ++j) {
            inf.readInt(-E4, E4, "x_i or y_i");
            if (j == 7) inf.readEoln();
            else inf.readSpace();
        }
    }
    for (int i = 0; i < 4; ++i) {
        inf.readInt(-E4, E4, "dist ori");
        if (i == 3) inf.readEoln();
        else inf.readSpace();
    }
    inf.readEof();
    return 0;
}
