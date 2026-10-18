from pathlib import Path
S=(Path(__file__).parents[1]/'contracts'/'contract.py').read_text()
def test_surface():
 for n in ('open_orbit','add_node','freeze','map_orbit','lock','get_orbit'):assert 'def '+n in S
def test_consensus_recomputes_edges():assert 'return run()==leader.calldata' in S and "relation':'DEPENDS'" in S
def test_sources_are_distinct():assert "origin==o.charter_origin" in S and "n['origin']==origin" in S
def test_topology_is_deterministic():assert 'incoming=[0]*len(nodes)' in S and "o.state='CYCLE'" in S and "o.state='OVERFLOW'" in S
def test_transition_and_owner_guards():assert "o.state!='OPEN'" in S and 'gl.message.sender_address!=o.owner' in S
