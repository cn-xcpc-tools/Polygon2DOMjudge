#include<iostream>
#include<cmath>
#include<queue>
#include<cstring>
#include<iomanip>
using namespace std;
#define MAXN 1007
#define x0 aff
#define y0 asd
#define x1 fda
#define y1 fad
#define CD const D
int n;
struct D {
	double x,y;
};
istream& operator>>(istream& os, D&pt) {os>>pt.x>>pt.y; return os;}
D box[MAXN][4];
D pos0, pos1;


#define EPS 1e-6
int dcmp(double x) {return (x>EPS)-(x<-EPS);}
D operator+(CD&a, CD&b) {return (D){a.x+b.x, a.y+b.y};}
D operator-(CD&a, CD&b) {return (D){a.x-b.x, a.y-b.y};}
D operator*(CD&a, double r) {return (D){a.x*r, a.y*r};}
D operator/(CD&a, double r) {return (D){a.x/r, a.y/r};}
double cross(CD&a, CD&b) {return a.x*b.y-a.y*b.x;}
double dot(CD&a, CD&b) {return a.x*b.x+a.y*b.y;}
double len(CD&a) {return sqrt(a.x*a.x+a.y*a.y);}
bool SegIntersec(CD&a, CD&b, CD&c, CD&d) {
	double c1=cross(b-a,c-a), c2=cross(b-a,d-a), c3=cross(d-c,a-c), c4=cross(d-c,b-c);
	return dcmp(c1)*dcmp(c2)<0 && dcmp(c3)*dcmp(c4)<0;
}
bool OnSeg(CD&p, CD&a, CD&b) {
	return dcmp(cross(a-p,b-p)) ==0 && dcmp(dot(a-p,b-p))<=0;
}

inline bool canconn(CD&a, CD&b) {
	for(int i=0; i<n; i++) {
		if((OnSeg(box[i][0],a,b) && OnSeg(box[i][2],a,b)) ||
			(OnSeg(box[i][1],a,b) && OnSeg(box[i][3],a,b)))
			return false;
		if(SegIntersec(box[i][0],box[i][1],a,b) || 
			SegIntersec(box[i][1],box[i][2],a,b) || 
			SegIntersec(box[i][2],box[i][3],a,b) || 
			SegIntersec(box[i][3],box[i][0],a,b))
			return false;
	}
	return true;
}
#define MAXM (MAXN*MAXN*16)
int hd[MAXN*4+3], to[MAXM], nxt[MAXM], en;
double le[MAXM];

inline void adde(int a, int b, double x) {
	nxt[en]=hd[a]; to[en]=b; hd[a]=en; le[en]=x; en++;
	nxt[en]=hd[b]; to[en]=a; hd[b]=en; le[en]=x; en++;
}

double d[MAXN*4+3];
bool vis[MAXN*4+3];
inline void dijkstra(int o) {
	int N=n*4+2;
	for(int i=0; i<N; i++) d[i]=2e33;
	memset(vis,0,sizeof(bool)*(n*4+2));
	d[o]=0;
	for(int i=1; i<N; i++) {
		int ch=-1;
		double v=2e33;
		for(int j=0; j<N; j++) if(!vis[j]) {
			if(d[j]<v) ch=j, v=d[j];
		}
		vis[ch]=1;
		for(int i=hd[ch]; ~i; i=nxt[i]) {
			int t=to[i];
			if(vis[t]) continue;
			if(d[t]>v+le[i]) d[t]=v+le[i];
		}
	}
}

int main() {
	ios::sync_with_stdio(0), cin.tie(0), cout.tie(0);
	cout << fixed << setprecision(20);
	cin >> n;
	for(int i=0; i<n; i++) {
		cin >> box[i][0] >> box[i][1] >> box[i][2] >> box[i][3];
	}
	cin >> pos0 >> pos1;
	memset(hd,-1,sizeof hd);
	for(int i=0; i<n; i++) {
		D a, b;
		for(int k=0; k<4; k++) {
			a=box[i][k];
			for(int j=i+1; j<n; j++) {
				for(int l=0; l<4; l++) {
					b=box[j][l];
					if(canconn(a,b)) {
						adde(i*4+k+2, j*4+l+2, len(b-a));
					}
				}
			}
			b=pos0;
			if(canconn(a,b)) adde(i*4+k+2, 0, len(b-a));
			b=pos1;
			if(canconn(a,b)) adde(i*4+k+2, 1, len(b-a));
			b=box[i][(k+1)%4];
			if(canconn(a,b)) adde(i*4+k+2, i*4+(k+1)%4+2, len(b-a));
		}
		a=pos0, b=pos1;
		if(canconn(a,b)) adde(0, 1, len(b-a));
	}
	dijkstra(0);
	cout << d[1] << '\n';
}
