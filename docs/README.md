# PhishGuard Documentation Index

Бұл бумада жобаның ағымдағы іске асқан бөліктері бойынша толық техникалық құжаттама бар.

## Құжаттар

1. [01-project-status.md](01-project-status.md)  
   Ағымдағы статус, орындалған фазалар, нақты нәтижелер.
2. [02-setup-and-runbook.md](02-setup-and-runbook.md)  
   Орнату, конфигурация, іске қосу командалары.
3. [03-architecture.md](03-architecture.md)  
   Жүйе архитектурасы, pipeline ағыны, модульдер.
4. [04-interfaces-and-reference.md](04-interfaces-and-reference.md)  
   Негізгі интерфейстер, DB схема, HTTP endpoint-тер.
5. [05-testing-and-metrics.md](05-testing-and-metrics.md)  
   Тест стратегиясы, орындалған тесттер, метрикалар.
6. [06-troubleshooting.md](06-troubleshooting.md)  
   Жиі кездесетін қателер және шешімдер.
7. [07-git-guide.md](07-git-guide.md)  
   Git-ке инициализациялау, commit/push, PR workflow.
8. [08-diploma-deliverables.md](08-diploma-deliverables.md)  
   Диплом қорғауға дайын материалдар чеклисті.
9. [09-phase5-quality-and-defense.md](09-phase5-quality-and-defense.md)  
   Phase 5 финал сапа есебі және қорғау сценариі.

## Жылдам бастау

```bash
python -m pip install -r requirements.txt
copy .env.example .env
python data/preprocess.py
python model/train.py --mode baseline
python model/evaluate.py --mode baseline
python main.py --once
python dashboard/app.py
```
