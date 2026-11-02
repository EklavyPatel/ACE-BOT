"""Paired UCI comparison; no external engines, analysis or opening book.
The short start sequences are fixed test fixtures, never loaded by the engine.
"""
import argparse,json,sys,time
from pathlib import Path
import chess,chess.engine,chess.pgn

def main():
 p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--candidate',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--seconds',type=float,default=.1);p.add_argument('--max-plies',type=int,default=240);p.add_argument('--output',type=Path,default=Path('comparison'))
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 fixtures=[[],['e4','e5'],['d4','d5','c4','e6'],['Nf3','Nf6','g3','g6']]
 records=[]
 for index,start in enumerate(fixtures):
  for colour in (chess.WHITE,chess.BLACK):
   b=chess.Board()
   for san in start:b.push_san(san)
   game=chess.pgn.Game.from_board(b);node=game.end();game.headers.update(Event='Paired local review',White='candidate' if colour else 'original',Black='original' if colour else 'candidate')
   engines={}
   for label,path in [('original',a.original),('candidate',a.candidate)]:
    engines[label]=chess.engine.SimpleEngine.popen_uci([sys.executable,str(path.resolve()/'engine/main.py')],timeout=3)
    engines[label].configure({'Move Overhead':0})
   counts={'candidate':0,'original':0};overruns=counts.copy();maximum={k:0.0 for k in counts};termination='move_cap';result='*';failure=None
   try:
    for ply in range(a.max_plies):
     outcome=b.outcome(claim_draw=True)
     if outcome:result=outcome.result();termination=outcome.termination.name;break
     label='candidate' if b.turn==colour else 'original';t=time.perf_counter()
     try:r=engines[label].play(b,chess.engine.Limit(time=a.seconds))
     except Exception as exc:
      failure=label+': '+type(exc).__name__;termination='engine_failure';result='0-1' if b.turn else '1-0';break
     elapsed=time.perf_counter()-t;counts[label]+=1;maximum[label]=max(maximum[label],elapsed)
     # Wall time includes IPC and scheduler delay. Report >50 ms excess separately.
     if elapsed>a.seconds+.05:overruns[label]+=1
     if r.move not in b.legal_moves:
      failure=label+': illegal_move';termination='engine_failure';result='0-1' if b.turn else '1-0';break
     b.push(r.move);node=node.add_variation(r.move)
    else:
     outcome=b.outcome(claim_draw=True)
     if outcome:result=outcome.result();termination=outcome.termination.name
   finally:
    for engine in engines.values():engine.quit()
   game.headers['Result']=result;game.headers['Termination']=termination
   if result=='*':status='unfinished'
   elif result=='1/2-1/2':status='draw'
   else:status='win' if (result=='1-0')==colour else 'loss'
   row=dict(game=len(records)+1,fixture=index,candidate_colour='white' if colour else 'black',result=result,candidate_result=status,termination=termination,plies=len(b.move_stack)-len(start),failure=failure,overruns_50ms=overruns,max_wall_seconds=maximum,move_counts=counts,seconds_per_move=a.seconds)
   records.append(row);(a.output/f'game-{len(records)}.pgn').write_text(str(game)+'\n');(a.output/'results.json').write_text(json.dumps(records,indent=2));print(json.dumps(row),flush=True)
 print(json.dumps({s:sum(r['candidate_result']==s for r in records) for s in ['win','draw','loss','unfinished']}),flush=True)
if __name__=='__main__':main()
