header = """services:

  serverhello:
    image: tigase/tigase-xmpp-server:8.1.2
    ports:
      - "8480:8080"
      - "5422:5222"
    environment:
      - DB_ROOT_USER=admin
      - DB_ROOT_PASS=admin
      - ADMIN_JID=admin@serverhello
      - ADMIN_PASSWORD=admin
    volumes:
      - ./tigase/config/tigase.conf:/home/tigase/tigase-server/etc/tigase.conf
      - ./tigase/config/config.tdsl:/home/tigase/tigase-server/etc/config.tdsl
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/rest/health"]
      interval: 15s
      timeout: 5s
      retries: 5
"""

nunmOfContainers = 10
numOfAgents = 100
agentsPerContainers = int(numOfAgents/nunmOfContainers)
repeats = 10
messageSize = 1024
commType = "cfp"
groupsize = 3

print(header)
for i in range(nunmOfContainers):
    print("""  mas{}:
    image: mas:latest
    build:
      context: .
    command: python -u main.py -f {} -t {} -n {} -r {} -x {} -i {} -c {} -g {}
    deploy:
      resources:
        limits:
          memory: 128MB

""".format(i, i * agentsPerContainers, (i+1) * agentsPerContainers - 1, numOfAgents, repeats, messageSize, "1" if i == nunmOfContainers - 1 else "0", commType, groupsize))


