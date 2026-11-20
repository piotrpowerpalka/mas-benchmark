import asyncio
from contextlib import suppress


CONNECT_TIMEOUT_SECONDS = 0.25


async def _close_connection(reader, writer):
    del reader
    writer.close()
    with suppress(OSError):
        await writer.wait_closed()


async def _tcp_port_ready(host, port):
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except (OSError, asyncio.TimeoutError):
        return False

    writer.close()
    with suppress(OSError):
        await writer.wait_closed()
    return True


class StartupBarrier:
    def __init__(self, args, coordinator_agent_id, local_agent_count):
        self.args = args
        self.coordinator_agent_id = coordinator_agent_id
        self.local_agent_count = local_agent_count
        self.ready = False
        self._event = asyncio.Event()
        self._local_ready_event = asyncio.Event()
        self._local_ready_agents = set()
        self._failure = None
        self._server = None

    def fail(self, agent_id, error, logger):
        if self._failure is None:
            self._failure = error
        logger.error(
            "uAgents startup preparation failed for agent%s: %s",
            agent_id,
            error,
        )
        self._local_ready_event.set()
        self._event.set()

    async def wait(self, agent_id, logger):
        self._local_ready_agents.add(agent_id)
        if len(self._local_ready_agents) == self.local_agent_count:
            self._local_ready_event.set()

        if agent_id == self.coordinator_agent_id:
            try:
                if self._failure is not None:
                    return False
                try:
                    await asyncio.wait_for(
                        self._local_ready_event.wait(),
                        timeout=self.args.startup_timeout,
                    )
                except asyncio.TimeoutError as error:
                    missing_agents = sorted(
                        set(
                            range(
                                self.coordinator_agent_id,
                                self.coordinator_agent_id + self.local_agent_count,
                            )
                        )
                        - self._local_ready_agents
                    )
                    raise TimeoutError(
                        "local agents did not become ready: {}".format(missing_agents)
                    ) from error
                if self._failure is not None:
                    return False
                self._server = await self._wait_for_containers()
                self.ready = True
            except (OSError, TimeoutError, asyncio.TimeoutError) as error:
                logger.error("uAgents readiness barrier failed: %s", error)
            finally:
                self._event.set()
        else:
            await self._event.wait()
        return self.ready

    async def _wait_for_containers(self):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.args.startup_timeout

        while not await _tcp_port_ready("127.0.0.1", self.args.port):
            if loop.time() >= deadline:
                raise TimeoutError("uAgents message server did not start")
            await asyncio.sleep(0.1)

        server = await asyncio.start_server(
            _close_connection,
            host="0.0.0.0",
            port=self.args.readiness_port,
        )
        try:
            while True:
                pending = []
                for container_id in range(self.args.container_count):
                    if container_id == self.args.container_index:
                        continue
                    if not await _tcp_port_ready(
                        "mas{}".format(container_id), self.args.readiness_port
                    ):
                        pending.append(container_id)

                if not pending:
                    return server
                if loop.time() >= deadline:
                    raise TimeoutError(
                        "uAgents containers did not become ready: {}".format(pending)
                    )
                await asyncio.sleep(0.1)
        except Exception:
            server.close()
            await server.wait_closed()
            raise
