# JADEX agent system – odpowiednik benchmarku SPADE

Projekt odwzorowuje logikę z przesłanych agentów SPADE:
- `InformAgent` – losowe wysyłanie `INFORM`
- `QueryAgent` – `QUERY_REF -> INFORM`
- `CfpAgent` – `CFP -> PROPOSE/REFUSE -> ACCEPT_PROPOSAL/REJECT_PROPOSAL`
- `InitAgent` – rozsyła sygnał startowy `Start`

## Uruchomienie

```bash
./gradlew run --args="--communication-type=inform --numagents=10 --groupsize=3 --repetitions-num=10 --content-size=1024 --seed=213742189290 --initag=1"
```

## Uwaga

Kod jest napisany pod **Jadex 4.0.241**. To celowy wybór: dokumentacja 4.x ma stabilne artefakty w Maven Central, podczas gdy linia 5.x/jadex-v jest nadal publikowana jako alpha.
