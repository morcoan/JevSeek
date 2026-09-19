"""Authored bounded semantic-dispatch batches; not a coding benchmark."""
from __future__ import annotations
import hashlib,json,random

DOMAINS={
'notifications':[
 ('addressed delivery','Sends an addressed envelope and asserts the intended recipient actually received it.','Checks HTTP200 on submission without inspecting who received the notification.','Confirm the addressed recipient receives the notification.','I need evidence of delivery to the right person, not merely an accepted request.'),
 ('replay deduplication','Submits the same logical send twice with the same idempotency token and asserts exactly one delivered message.','Checks every attempt has a unique tracking ID; it does not count logical deliveries.','Verify that replaying one logical send cannot duplicate delivery.','Two attempts for one notification must still produce just one delivered message.'),
 ('international text','Roundtrips accented Latin and Japanese message text through actual encoding and decoding, asserting exact equality.','Roundtrips ASCII letters only; it does not exercise non-ASCII characters.','Verify international characters survive the wire unchanged.','Make sure accents and Japanese glyphs survive serialization and decoding intact.'),
 ('latest artifact','Runs the behavior regression against the current artifact digest and asserts the receipt cites that exact digest.','Reads a green test receipt from a previous build without running or comparing the current artifact.','Verify the current artifact was tested, not just an older build.','A past green run is insufficient: establish that the tested digest is the artifact we have now.'),
 ('secret redaction','Injects a synthetic secret and asserts it is absent from the complete captured diagnostic stream.','Checks only the first log line for a redaction marker without scanning the remaining captured output.','Verify the synthetic secret never appears anywhere in captured diagnostics.','Search the entire captured diagnostic output for the canary secret; checking its prefix is not enough.'),
 ('per-recipient ordering','Sends numbered events to one recipient under parallel delivery and asserts their observed sequence is preserved.','Checks only the total number of events delivered, without comparing their order.','Verify parallel delivery preserves each recipient\'s event sequence.','Receiving the correct count is not enough; consecutive event numbers must arrive in order.')],
'storage':[
 ('byte preservation','Stores arbitrary binary bytes, reads them back, and asserts byte-for-byte equality.','Checks the returned object length matches the input length without comparing contents.','Verify storing and reading an object preserves every byte.','The size can match while bytes change; test exact binary roundtrip identity.'),
 ('tenant isolation','Uses two tenant credentials and asserts one tenant cannot read the other tenant\'s object even when its name is known.','Checks tenant object names have different prefixes without attempting cross-tenant reads.','Verify one tenant cannot read another tenant\'s known object.','Try the other tenant\'s credentials against a known object and require access denial.'),
 ('concurrent conditional writes','Issues two writes with the same prior version token and asserts exactly one succeeds while the other reports a version conflict.','Runs two writes sequentially without a version condition and checks both responses succeeded.','Verify concurrent writes with a shared old version cannot both succeed.','Two writers using the same stale version must not both overwrite the object successfully.'),
 ('stored encryption','Inspects the persisted storage representation of a test object and asserts its plaintext canary is not stored unencrypted.','Checks HTTPS transport configuration but does not inspect the persisted object representation.','Verify the persisted object is encrypted, not merely transported over TLS.','Secure transport is not enough: inspect the stored representation for unencrypted canary data.'),
 ('retention expiry','Advances the test clock beyond the stated retention duration, then attempts an object read and asserts it is unavailable.','Checks a retention-duration field is present in metadata without advancing time or attempting a read.','Verify the object cannot be read after its retention period expires.','After the retention deadline passes, actually try to fetch the object and require unavailability.'),
 ('replica deletion','Deletes a test object and queries every configured replica, asserting none still returns the deleted object.','Checks the primary deletion endpoint returned success without querying replicas.','Verify deletion removes the object from every configured replica.','A successful primary delete does not suffice; no configured replica may still serve the object.')],
'pipeline':[
 ('atomic publication','Injects a failure midway through a transaction and asserts readers observe either the complete prior snapshot or the complete new snapshot, never a partial mixture.','Checks final row count on a successful run without injecting a transaction failure.','Verify failed publication cannot expose a partially committed snapshot.','Interrupt the commit and check readers never see an old/new row mixture.'),
 ('missing versus zero','Processes explicit zero and missing-value inputs and asserts they remain distinct outputs rather than both becoming null.','Processes only missing inputs and checks they become null; zero is never exercised.','Verify numeric zero is not confused with a missing value.','Feed both absent data and an actual zero; the outputs must preserve that distinction.'),
 ('stable tie ordering','Sorts multiple records with equal primary keys and asserts their original relative order is retained.','Checks primary keys are nondecreasing without examining the order within equal-key groups.','Verify sorting keeps original order among equal-key rows.','Tied sort keys must not arbitrarily rearrange rows; test their relative order.'),
 ('event idempotence','Replays the same immutable event ID and asserts the materialized state is changed only once.','Checks each delivery attempt gets a distinct trace ID without observing materialized-state duplication.','Verify replaying one immutable event does not apply its effect twice.','Repeated transport attempts for one event must cause only one materialized-state update.'),
 ('quoted-field parsing','Parses a field containing a delimiter inside quotes and asserts it remains a single intact field.','Parses delimiter-separated rows containing no quoted embedded delimiters.','Verify a quoted delimiter stays inside one field.','A delimiter inside quotation marks must not split the value into additional columns.'),
 ('timezone instant','Parses timestamps with nonzero UTC offsets and asserts conversion preserves the represented absolute instant.','Checks timestamps retain their local clock numbers while discarding offset information.','Verify timezone conversion preserves the instant in time.','Different offsets may change clock numbers; conversion must retain the same absolute moment.')]
}


def batch(seed,domain,phase):
 rng=random.Random(seed);entries=DOMAINS[domain];rows=[];hidden={};targets={}
 for i,(topic,good,weak,q0,q1) in enumerate(entries):
  for supported,description in [(True,good),(False,weak)]:
   key='c'+format(rng.getrandbits(24),'06x');rows.append((key,{'description':description,'call':{'tool':'run_registered_probe','arguments':{'artifact_id':'artifact-'+str(seed),'probe_id':key}}}));hidden[key]=[i] if supported else []
   if supported:targets[i]=key
 rng.shuffle(rows);catalog=dict(rows);catalog['NONE']={'description':'No single available procedure directly exercises the entire requested behavior. Do not combine or invent procedures.','call':None}
 order=list(range(6));rng.shuffle(order);queries={};gold={}
 for n,i in enumerate(order):
  key='q'+str(n);queries[key]=entries[i][3 if phase=='development' else 4];gold[key]=targets[i]
 a,b=rng.sample(range(6),2);queries['q6']='One single procedure must cover BOTH of these complete requests: ('+entries[a][3]+') AND ('+entries[b][3]+').';gold['q6']='NONE'
 queries['q7']='Select a procedure that verifies an administrator\'s hardware security key was physically used to authorize this operation.';gold['q7']='NONE'
 return {'id':domain+'-'+str(seed),'domain':domain,'phase':phase,'catalog':catalog,'queries':queries,'hidden':{'coverage':hidden,'gold':gold}}


def fixtures():
 domains=list(DOMAINS);dev=[batch(831000+i,domains[i%3],'development') for i in range(4)];test=[batch(841000+i,domains[i%3],'confirmation') for i in range(12)]
 return dev+test


def fingerprint():return hashlib.sha256(json.dumps(fixtures(),ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def evaluate(t,answer):
 answer=answer if isinstance(answer,dict) else {};gold=t['hidden']['gold'];correct=sum(answer.get(k)==v for k,v in gold.items());none_ids=[k for k,v in gold.items() if v=='NONE']
 return {'correct':correct,'total':len(gold),'batch_correct':correct==len(gold),'none_correct':sum(answer.get(k)=='NONE' for k in none_ids),'none_total':len(none_ids),
         'false_none':sum(answer.get(k)=='NONE' and v!='NONE' for k,v in gold.items()),'invalid':sum(answer.get(k) not in t['catalog'] if isinstance(answer.get(k),str) else True for k in gold)}
