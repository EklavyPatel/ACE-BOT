import sys,json,time,random,chess
sys.path.insert(0,sys.argv[1])
from source.search import Searcher,Limits
boards=[chess.Board()]
b=chess.Board()
for san in ['e4','e5','Nf3','Nc6','Bc4','Bc5','d3','Nf6']:
 b.push_san(san)
boards.append(b.copy())
rng=random.Random(54)
for _ in range(6):
 b=chess.Board()
 for j in range(12): b.push(rng.choice(list(b.legal_moves)))
 boards.append(b)
out=[]
for b in boards:
 r=Searcher().search(b,Limits(None,None,3))
 out.append(dict(fen=b.fen(),move=r.move.uci(),score=r.score,nodes=r.nodes,seconds=r.elapsed))
print(json.dumps(out))
