import sys


def gen_compose(xmpp, numOfContainers, numOfAgents, repeats, messageSize, commType, groupsize, memsize="128MB", cpus="1", period="100"): 
  """
  Generate a Docker Compose configuration file for multi-agent system (MAS) benchmark.
    This function creates a Docker Compose YAML configuration that sets up a distributed
    multi-agent system with either Tigase or Prosody XMPP server and multiple MAS containers.
    Args:
      xmpp (str): XMPP server type to use. Either "prosody" or "tigase".
      numOfContainers (int): Number of MAS containers to generate in the composition.
      numOfAgents (int): Total number of agents to distribute across containers.
      repeats (int): Number of times to repeat the benchmark/test.
      messageSize (int or str): Size of messages for communication between agents.
      commType (str): Type of communication protocol to use.
      groupsize (int or str): Size of agent groups for communication.
      memsize (str, optional): Memory limit per container. Defaults to "128MB".
      cpus (str, optional): CPU limit per container. Defaults to "1".
      period (str, optional): Period for the ticker behavior. Defaults to "100".
    Returns:
      str: A complete Docker Compose YAML configuration as a string, including:
        - XMPP server service configuration
        - Multiple MAS agent containers with distributed agent ranges
        - Network configuration (if using Prosody)
        - Resource limits for each container
    Example:
      >>> compose_config = gen_compose("prosody", 3, 30, 5, 1024, "tcp", 5, "256MB", "0.5", "200")
      >>> # Returns YAML string with 3 containers, 10 agents each

  """  
  rv = ""
  agentsPerContainers = numOfAgents // numOfContainers

  header_tigase = """services:

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

  header_prosody = """services:

    serverhello:
      image: prosody/prosody:latest
      container_name: serverhello
      hostname: serverhello
      environment:
        PROSODY_VIRTUAL_HOSTS: "serverhello"
      ports:
        - "5222:5222"  # Port XMPP
        - "5269:5269"  # Server-to-server communication (optional)
        - "5280:5280"  # HTTP (optional, for web admin or BOSH)
      volumes:
        - ./prosody/conf/prosody.cfg.lua:/prosody/conf.d/prosody.cfg.lua
        - ./prosody/conf/prosody.cfg.lua:/etc/prosody/prosody.cfg.lua
        - ./prosody/certs:/etc/prosody/certs
  """

  header_jade = """services:
    serverhello: 
      image: jadeserver:latest
      ports:
        - "1099:1099"
        - "7778:7778"
      container_name: serverhello
      hostname: serverhello
      build:
        context: .
        dockerfile: Dockerfile
      command: java -cp /app/jade.jar:. jade.Boot -local-host  serverhello -port 1099  
      deploy:
        resources:
          limits:
            memory: 128MB
"""

  if (xmpp == "prosody"):  rv += header_prosody
  elif (xmpp == "tigase"): rv += header_tigase
  elif (xmpp == "jade"):   rv += header_jade
  else:
    raise ValueError("Unsupported XMPP server type: {}".format(xmpp))

  if (xmpp == "prosody" or xmpp == "tigase"):
    for i in range(numOfContainers):
        rv += """
    mas{}:
      image: mas:latest
      build:
        context: .
      container_name: mas{}
      hostname: mas{}
      command: python -u main.py -f {} -t {} -n {} -r {} -x {} -i {} -c {} -g {} -p {}
      deploy:
        resources:
          limits:
            memory: {}
            cpus: {}
      depends_on:
      - serverhello
    """.format(i, i, i, i * agentsPerContainers, (i+1) * agentsPerContainers - 1, numOfAgents, repeats, messageSize, "1" if i == numOfContainers - 1 else "0", commType, groupsize, period, memsize, cpus)

  if (xmpp == "jade"):
    for i in range(numOfContainers):
        rv += """
    mas{}:
        image: jademas:latest
        build:
          context: .
          dockerfile: Dockerfile
        container_name: mas{}
        hostname: mas{}
        command: >
          sh -c '
            until nc -z serverhello 1099; do
              echo "Waiting for serverhello TCP 1099...";
              sleep 1;
            done
            exec java -cp /app/jade.jar:. Main -f {} -t {} -n {} -r {} -x {} -i {} -c {} -g {} -p {} --container-name mas{}
          '
        deploy:
          resources:
            limits:
              memory: {}
              cpus: {}
    """.format(i, i, i, i * agentsPerContainers, (i+1) * agentsPerContainers - 1, numOfAgents, repeats, messageSize, "1" if i == numOfContainers - 1 else "0", commType, groupsize, period, i, memsize, cpus)
 
  return rv

def compose_tofile(dcname, x, nc, na, repeats, ms, ct, gs, memsize, cpus, period):
  """
  Generate a Docker Compose configuration file with specified parameters.

  This function generates Docker Compose content based on the provided configuration
  parameters and writes it to a file with a descriptive filename.

  Args:
    dcname (str): Name of the Docker Compose configuration.
    x (str): XMPP server identifier.
    nc (int): Number of containers.
    na (int): Number of agents.
    repeats (int): Number of repetitions.
    ms (int): Message size.
    ct (str): Communication type ["cfp", "inform", "query"].
    gs (str): group size - only for "cfp" communication type.
    memsize (str): Memory size allocation.
    cpus (str): CPU allocation.
    period (str): Period for the ticker behavior.

  Returns:
    None

  Side Effects:
    Creates and writes to a file named: docker-compose-{nc}c-{na}a-{ms}ms-{ct}-{gs}g-{x}-{memsize}-{cpus}-p{period}.yml
    The file contains the generated Docker Compose configuration content.

  Raises:
    IOError: If the file cannot be written to the filesystem.
  """
  compose_content = gen_compose(x, nc, na, repeats, ms, ct, gs, memsize, cpus, period)
  with open(dcname, "w") as f:
      f.write(compose_content)


if __name__ == "__main__":
  if len(sys.argv) != 12:
    print("Usage: python gen_compose.py <dcname> <xmpp> <num_containers> <num_agents> <repeats> <message_size> <comm_type> <group_size> <memsize> <cpus> <period>")
    sys.exit(1)

  compose_tofile(
    sys.argv[1],           # dcname
    sys.argv[2],           # xmpp
    int(sys.argv[3]),      # num_containers
    int(sys.argv[4]),      # num_agents
    int(sys.argv[5]),      # repeats
    int(sys.argv[6]),      # message_size
    sys.argv[7],           # comm_type
    sys.argv[8],           # group_size
    sys.argv[9],           # memsize
    sys.argv[10],          # cpus
    sys.argv[11]           # period
  )
  print(f"Docker Compose file generated successfully!")