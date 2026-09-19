"""New synthetic semantic-constraint tasks; no tasks from the earlier plan pilot.
Expected results use Python, not reference SQL. Providers see schema/requirements
only. This is a 12-family pilot, not a representative coding benchmark.
"""
from collections import Counter
import random
import sqlite3

SCHEMA='''SQLite schema (all integers unless TEXT is stated):
people(id PRIMARY KEY, team TEXT NOT NULL)
orders(id PRIMARY KEY, person_id, day NOT NULL, category TEXT NOT NULL, amount NOT NULL)
payments(id PRIMARY KEY, order_id, day NOT NULL, amount NOT NULL)
required(team TEXT NOT NULL, category TEXT NOT NULL)
status(id PRIMARY KEY, person_id, day NOT NULL, state TEXT NOT NULL)
Orders have strictly positive amounts; payments have nonnegative amounts. Days
are integer calendar days. There are no foreign keys: references may be NULL or
orphan. Multiple payments per order and duplicate required rows can exist.
Multiple status rows can share a person/day: greatest status.id is latest then.
Only actual people and their actual orders/payments count unless specified.
Return exactly requested columns. Output row ordering is immaterial. Query must
work for arbitrary data satisfying this schema, not a particular example.
'''
TASKS=[
 ('fanout_totals','For EVERY person output (id,ordered,paid). ordered is the sum of their order amounts, counting each order once. paid is the sum of all payments attached to those orders. Missing sums are zero. Multiple payments must not multiply order amounts.'),
 ('all_orders_funded','Return id of each person with at least one order and with EVERY individual order fully funded by its own payments. Funded means sum of attached payment amounts >= that order amount. An overpayment on one order cannot compensate for another; missing payments sum to zero.'),
 ('exact_categories','Return person id when their SET of purchased categories equals EXACTLY the required category SET for their team: none missing and none extra. Duplicate orders/required rows do not matter. Empty equals empty; people with no orders qualify only when their team has no requirements.'),
 ('running_net','For each person and day with an order or a valid attached payment, output (id,day,net). net is cumulative payment amount minus cumulative order amount through that calendar day inclusive. Same-day items all count once. Missing other days are not emitted. Payments may precede order day; still count on their own day.'),
 ('threshold_first','For EVERY person output (id,crossing_day). crossing_day is the earliest calendar day cumulative payments attached to their orders reaches at least 60, or NULL if never. Count payments on their payment day, including before order day. All same-day payments contribute together.'),
 ('status_asof','For EVERY person output (id,active_orders), count of their orders for which their latest status AS OF that order day is active. Status ordered by (day,id); status day must be <= order day. No prior status means NOT active. State values are active/inactive. Multiple historical rows must not multiply orders.'),
 ('first_payment_day','For EVERY order belonging to a real person output (order_id,first_day,total). Consider only attached payments with payment.day >= order.day. first_day is earliest such payment day or NULL; total is sum of payments on THAT first day only, or zero. Earlier payments and later days must not affect total.'),
 ('team_fraction','For EVERY person output (id,fraction): their total order amount divided by their whole team total order amount, including all team members. Payment rows irrelevant. Return real division, zero share for a person without orders when team total > 0, and NULL when the entire team total is zero.'),
 ('largest_payment_day','For EVERY person output (id,day,total), choosing the day with greatest sum of attached payments for that person. On equal totals choose the LATEST day. If no payment rows, output (id,NULL,0). Days whose payments all have zero amount still count as payment days.'),
 ('ordered_sequence','Return person id if they have a red-category order on a day r and a blue-category order on a STRICTLY later day b, with NO green-category order on ANY day in [r,b] inclusive. Multiple candidate pairs allowed: one valid pair suffices. Same-day red/blue alone is not a valid pair.'),
 ('rolling_distinct','For each person/day with at least one order output (id,day,categories): number of DISTINCT categories they purchased in calendar days [day-6,day] inclusive. Repeated orders/categories and missing calendar days must not be treated as extra ranks. One output per actual person/order-day.'),
 ('cohort_retention','For each cohort day c, output (cohort_day,people_count,retained_count). A person belongs to c = their first order day. Retained means they have any order during [c+7,c+13] inclusive. Count each person once, not orders. Include cohorts with zero retained. Exclude people with no orders.'),
]


def fixture(seed):
    r=random.Random(9700+seed)
    people=[(i,'ABCD'[(i-1)//3]) for i in range(1,11)]
    orders=[(1,1,1,'red',20),(2,1,3,'blue',30),(3,2,3,'red',50),(4,2,10,'blue',50)]
    orders += [(i,r.choice([None,99,2,3,4,5,6,7,8]),r.randrange(1,21),r.choice(['red','blue','green']),r.choice([5,10,20,40])) for i in range(5,45)]
    payments=[(1,1,1,5),(2,1,2,15),(3,2,10,10),(4,2,10,20),(5,3,1,60)]
    payments += [(i,r.choice([None,999]+list(range(1,45))),r.randrange(1,26),r.choice([0,1,5,10,20])) for i in range(6,85)]
    required=[('A','red'),('A','blue'),('A','red'),('B','red')]
    status=[]
    for i in range(1,11):
        for d,state in [(0,'active'),(7,'inactive'),(7,r.choice(['active','inactive'])),(14,'active')]:
            status.append((len(status)+1,i,d,state))
    status += [(41,None,3,'active'),(42,99,4,'active')]
    return people,orders,payments,required,status


def expected(name,data):
    people,orders,payments,required,status=data
    po={i:[o for o in orders if o[1]==i] for i,_ in people}
    pp={i:[p for p in payments if p[1] in {o[0] for o in po[i]}] for i,_ in people}
    if name=='fanout_totals':return [(i,sum(o[4] for o in po[i]),sum(p[3] for p in pp[i])) for i,_ in people]
    if name=='all_orders_funded':return [(i,) for i,_ in people if po[i] and all(sum(p[3] for p in payments if p[1]==o[0])>=o[4] for o in po[i])]
    if name=='exact_categories':return [(i,) for i,t in people if {o[3] for o in po[i]}=={c for team,c in required if team==t}]
    if name=='running_net':return [(i,d,sum(p[3] for p in pp[i] if p[2]<=d)-sum(o[4] for o in po[i] if o[2]<=d)) for i,_ in people for d in {o[2] for o in po[i]}|{p[2] for p in pp[i]}]
    if name=='threshold_first':return [(i,next((d for d in sorted({p[2] for p in pp[i]}) if sum(p[3] for p in pp[i] if p[2]<=d)>=60),None)) for i,_ in people]
    if name=='status_asof':
        out=[]
        for i,_ in people:
            count=0
            for o in po[i]:
                states=[s for s in status if s[1]==i and s[2]<=o[2]]
                count+=bool(states and max(states,key=lambda s:(s[2],s[0]))[3]=='active')
            out.append((i,count))
        return out
    if name=='first_payment_day':
        out=[]
        for i,_ in people:
            for o in po[i]:
                ps=[p for p in payments if p[1]==o[0] and p[2]>=o[2]]
                d=min((p[2] for p in ps),default=None)
                out.append((o[0],d,sum(p[3] for p in ps if p[2]==d)))
        return out
    if name=='team_fraction':
        totals={i:sum(o[4] for o in po[i]) for i,_ in people}
        return [(i,totals[i]/den if (den:=sum(totals[j] for j,t in people if t==team)) else None) for i,team in people]
    if name=='largest_payment_day':
        out=[]
        for i,_ in people:
            totals={d:sum(p[3] for p in pp[i] if p[2]==d) for d in {p[2] for p in pp[i]}}
            d=max(totals,key=lambda d:(totals[d],d)) if totals else None
            out.append((i,d,totals[d] if totals else 0))
        return out
    if name=='ordered_sequence':return [(i,) for i,_ in people if any(a[3]=='red' and b[3]=='blue' and a[2]<b[2] and not any(c[3]=='green' and a[2]<=c[2]<=b[2] for c in po[i]) for a in po[i] for b in po[i])]
    if name=='rolling_distinct':return [(i,d,len({o[3] for o in po[i] if d-6<=o[2]<=d})) for i,_ in people for d in {o[2] for o in po[i]}]
    if name=='cohort_retention':
        cohorts={i:min(o[2] for o in po[i]) for i,_ in people if po[i]}
        return [(d,sum(c==d for c in cohorts.values()),sum(c==d and any(d+7<=o[2]<=d+13 for o in po[i]) for i,c in cohorts.items())) for d in set(cohorts.values())]
    raise ValueError(name)


DDL='''CREATE TABLE people(id INTEGER PRIMARY KEY,team TEXT NOT NULL);
CREATE TABLE orders(id INTEGER PRIMARY KEY,person_id INTEGER,day INTEGER NOT NULL,category TEXT NOT NULL,amount INTEGER NOT NULL);
CREATE TABLE payments(id INTEGER PRIMARY KEY,order_id INTEGER,day INTEGER NOT NULL,amount INTEGER NOT NULL);
CREATE TABLE required(team TEXT NOT NULL,category TEXT NOT NULL);
CREATE TABLE status(id INTEGER PRIMARY KEY,person_id INTEGER,day INTEGER NOT NULL,state TEXT NOT NULL);'''


def execute(sql,data):
    db=sqlite3.connect(':memory:')
    try:
        db.executescript(DDL)
        for table,rows in zip(['people','orders','payments','required','status'],data):
            if rows:db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in rows[0])})',rows)
        db.commit();db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        funcs={'abs','avg','coalesce','count','dense_rank','first_value','ifnull','lag','last_value','lead','max','min','nullif','nth_value','ntile','percent_rank','rank','round','row_number','sign','sum','total','iif'}
        db.set_authorizer(lambda act,a,b,c,d:sqlite3.SQLITE_OK if act in allowed and (act!=sqlite3.SQLITE_FUNCTION or str(b).lower() in funcs) else sqlite3.SQLITE_DENY)
        ticks=0
        def guard():
            nonlocal ticks
            ticks+=1;return int(ticks>5000)
        db.set_progress_handler(guard,1000)
        result=db.execute(sql).fetchmany(10001)
        if len(result)>10000:raise ValueError('row_limit')
        return result
    finally:db.close()


def normalized(rows):
    return Counter(tuple(round(v,8) if isinstance(v,float) else v for v in row) for row in rows)


def evaluate(name,sql):
    if not isinstance(sql,str) or not 0<len(sql)<=16000:return {'pass':False,'error':'format'}
    for seed in range(20):
        data=fixture(seed)
        try:result=execute(sql,data)
        except Exception as exc:return {'pass':False,'seed':seed,'error':type(exc).__name__}
        if normalized(result)!=normalized(expected(name,data)):return {'pass':False,'seed':seed,'error':'wrong_result'}
    return {'pass':True,'fixtures':20}
