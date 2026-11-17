package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

public final class AgentDirectory {
    private static final AtomicInteger NEXT_INDEX = new AtomicInteger(0);
    private static final Map<Integer, IComponentIdentifier> AGENTS = new ConcurrentHashMap<>();
    private static final AtomicInteger ACTIVE_WORKERS = new AtomicInteger(0);

    private AgentDirectory() {
    }

    public static int registerWorker(IComponentIdentifier id) {
        int index = NEXT_INDEX.getAndIncrement();
        AGENTS.put(index, id);
        ACTIVE_WORKERS.incrementAndGet();
        return index;
    }

    public static void unregisterWorker(int index) {
        AGENTS.remove(index);
        int left = ACTIVE_WORKERS.decrementAndGet();
        if (left <= 0) {
            System.exit(0);
        }
    }

    public static int countWorkers() {
        return AGENTS.size();
    }

    public static List<IComponentIdentifier> getPeers(int selfIndex) {
        return AGENTS.entrySet().stream()
                .filter(e -> e.getKey() != selfIndex)
                .sorted(Map.Entry.comparingByKey())
                .map(Map.Entry::getValue)
                .collect(Collectors.toList());
    }

    public static IComponentIdentifier randomPeer(int selfIndex) {
        List<IComponentIdentifier> peers = getPeers(selfIndex);
        if (peers.isEmpty()) {
            return null;
        }
        return peers.get(ThreadLocalRandom.current().nextInt(peers.size()));
    }

    public static List<IComponentIdentifier> randomGroup(int selfIndex, int groupSize) {
        List<IComponentIdentifier> peers = new ArrayList<>(getPeers(selfIndex));
        if (peers.isEmpty()) {
            return Collections.emptyList();
        }
        Collections.shuffle(peers);
        return peers.subList(0, Math.min(groupSize, peers.size()));
    }

    public static List<IComponentIdentifier> allWorkers() {
        return AGENTS.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(Map.Entry::getValue)
                .collect(Collectors.toList());
    }
}
