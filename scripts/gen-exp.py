from gen_compose import *

c = [1, 10, 100]
a = [1000]
mess = [1024**2]
comm = ["inform"]
xmpp = ["prosody", "tigase"]
repeats = 100
group = [30]

memsize="1GB"
cpus="2"

for nc in c:
    for na in a:
        for ms in mess:
            for ct in comm:
                for gs in group:
                    for x in xmpp:
                        print("Generating for: containers={}, agents={}, msgsize={}, commtype={}, xmpp={}, groupsize={}".format(nc, na, ms, ct, x, gs))
                        
                        compose_content = gen_compose(x, nc, na, repeats, ms, ct, gs, memsize)
                        filename = "docker-compose-{}c-{}a-{}ms-{}-{}g-{}-{}-{}.yml".format(nc, na, ms, ct, gs, x, memsize, cpus)
                        with open(filename, "w") as f:
                            f.write(compose_content)

                        
