#include<iostream>
#include<cassert>
#include "testlib.h"
using namespace std;

const int MAXN=207;

struct D { int x,y; };
D box[MAXN][4];
#define CD const D
D operator+(CD&a, CD&b) {return (D){a.x+b.x, a.y+b.y};}
D operator-(CD&a, CD&b) {return (D){a.x-b.x, a.y-b.y};}
D operator*(CD&a, int b) {return (D){a.x*b, a.y*b};}
int cross(CD&a, CD&b) {return a.x*b.y-a.y*b.x;}
bool in(int x, int y, int i) {
	D p=(D){x,y};
	for(int k=0; k<4; k++) {
		if(cross((box[i][(k+1)%4]-box[i][k]), p-box[i][k])<=0)
			return false;
	}
	return true;
}

int main(int argc, char* argv[]) {
	registerValidation(argc, argv);
	int n; cin >> n;
	assert(n<=200 && n>=0);
	for(int i=0; i<n; i++) {
		cin >> box[i][0].x >> box[i][0].y;
		cin >> box[i][1].x >> box[i][1].y;
		cin >> box[i][2].x >> box[i][2].y;
		cin >> box[i][3].x >> box[i][3].y;
		assert(abs(box[i][0].x) <=10000);
		assert(abs(box[i][0].y) <=10000);
		assert(abs(box[i][1].x) <=10000);
		assert(abs(box[i][1].y) <=10000);
		assert(abs(box[i][2].x) <=10000);
		assert(abs(box[i][2].y) <=10000);
		assert(abs(box[i][3].x) <=10000);
		assert(abs(box[i][3].y) <=10000);
	}
	for(int i=0; i<n; i++) {
		for(int j=0; j<i; j++) {
			for(int k=0; k<4; k++) {
				assert(!in(box[j][k].x,box[j][k].y,i));
				assert(!in(box[i][k].x,box[i][k].y,j));
			}
		}
	}
	
	for(int j=0; j<2; j++) {
		int x,y; cin >> x >> y;
		assert(abs(x)<=10000);
		assert(abs(y)<=10000);
		for(int i=0; i<n; i++) {
			assert(!in(x,y,i));
		}
	}
	cout << "ok\n";
}
